import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')
const RUN_TIMEOUT_MS = 15 * 60 * 1000
const MAX_BODY_BYTES = 100_000
const MAX_LOG_CHARS = 40_000

function resolvePythonPath() {
  const candidates = [
    path.join(REPO_ROOT, '.venv', 'Scripts', 'python.exe'),
    path.join(REPO_ROOT, '.venv', 'bin', 'python'),
  ]
  return candidates.find((candidate) => existsSync(candidate)) ?? 'python'
}

function isLoopback(address) {
  return address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1'
}

function sendJson(response, status, payload) {
  response.statusCode = status
  response.setHeader('Content-Type', 'application/json')
  response.end(JSON.stringify(payload))
}

function resolveContained(value, field) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${field} is required`)
  const resolved = path.resolve(REPO_ROOT, value)
  if (resolved !== REPO_ROOT && !resolved.startsWith(REPO_ROOT + path.sep)) {
    throw new Error(`${field} must stay inside the project directory`)
  }
  return resolved
}

export function prepareManifest(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('manifest must be an object')
  if (!Array.isArray(input.scenes) || input.scenes.length === 0) throw new Error('manifest.scenes must be a non-empty array')

  const manifest = structuredClone(input)
  manifest.output = resolveContained(manifest.output, 'manifest.output')
  manifest.work_dir = resolveContained(manifest.work_dir, 'manifest.work_dir')
  manifest.scenes.forEach((scene, index) => {
    if (!scene || typeof scene !== 'object' || Array.isArray(scene)) throw new Error(`scene ${index + 1} must be an object`)
    const sources = ['url', 'image', 'video'].filter((field) => typeof scene[field] === 'string' && scene[field].trim())
    if (sources.length !== 1) throw new Error(`scene ${index + 1} must define exactly one source`)
    const source = sources[0]
    if (source === 'url') {
      let parsed
      try { parsed = new URL(scene.url) } catch { throw new Error(`scene ${index + 1} has an invalid URL`) }
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error(`scene ${index + 1} URL must use http or https`)
      scene.url = parsed.toString()
    } else {
      scene[source] = resolveContained(scene[source], `scene ${index + 1}.${source}`)
      if (!existsSync(scene[source])) throw new Error(`scene ${index + 1} source file was not found`)
    }
    if (scene.narration) {
      scene.narration = resolveContained(scene.narration, `scene ${index + 1}.narration`)
      if (!existsSync(scene.narration)) throw new Error(`scene ${index + 1} narration file was not found`)
    }
  })
  return manifest
}

function registerMiddleware(server) {
  server.middlewares.use('/api/run-render-job', (request, response) => {
    if (request.method !== 'POST') return sendJson(response, 405, { error: 'Method not allowed' })
    if (!isLoopback(request.socket.remoteAddress)) return sendJson(response, 403, { error: 'Forbidden: local requests only' })

    let body = ''
    let tooLarge = false
    request.on('data', (chunk) => {
      body += chunk
      if (body.length > MAX_BODY_BYTES) tooLarge = true
    })
    request.on('end', () => {
      if (tooLarge) return sendJson(response, 413, { error: 'Request body is too large' })

      let payload
      let manifest
      try {
        payload = JSON.parse(body)
        manifest = prepareManifest(payload?.manifest)
      } catch (error) {
        return sendJson(response, 400, { error: error instanceof Error ? error.message : 'Invalid request' })
      }

      const manifestPath = path.join(manifest.work_dir, 'frontend-job.json')
      try {
        mkdirSync(manifest.work_dir, { recursive: true })
        writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8')
      } catch (error) {
        return sendJson(response, 500, { error: `Could not save manifest: ${error.message}` })
      }

      const child = spawn(resolvePythonPath(), ['-m', 'pipeline.render_job', manifestPath], {
        cwd: REPO_ROOT,
        env: {
          ...process.env,
          ...(typeof payload.password === 'string' && payload.password ? { MPOSTELE_PASSWORD: payload.password } : {}),
        },
        windowsHide: true,
      })
      let stdout = ''
      let stderr = ''
      let timedOut = false
      child.stdout.on('data', (chunk) => { if (stdout.length < MAX_LOG_CHARS) stdout += chunk.toString() })
      child.stderr.on('data', (chunk) => { if (stderr.length < MAX_LOG_CHARS) stderr += chunk.toString() })
      const timeout = setTimeout(() => {
        timedOut = true
        child.kill()
      }, RUN_TIMEOUT_MS)

      child.on('close', (code) => {
        clearTimeout(timeout)
        if (timedOut) return sendJson(response, 504, { error: 'Render job timed out', stdout, stderr })
        sendJson(response, 200, {
          code,
          stdout,
          stderr,
          outputPath: path.relative(REPO_ROOT, manifest.output),
          manifestPath: path.relative(REPO_ROOT, manifestPath),
        })
      })
      child.on('error', (error) => {
        clearTimeout(timeout)
        sendJson(response, 500, { error: `Failed to start process: ${error.message}` })
      })
    })
  })
}

export function renderJobRunPlugin() {
  return {
    name: 'mpostele-local-render-job-runner',
    configureServer: registerMiddleware,
    configurePreviewServer: registerMiddleware,
  }
}
