import { spawn } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO_ROOT = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')
const RUN_TIMEOUT_MS = 30 * 60 * 1000
const MAX_BODY_BYTES = 30_000
const MAX_LOG_CHARS = 40_000
const runs = new Map()

function resolvePythonPath() {
  const candidates = [path.join(REPO_ROOT, '.venv', 'Scripts', 'python.exe'), path.join(REPO_ROOT, '.venv', 'bin', 'python')]
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
  if (resolved !== REPO_ROOT && !resolved.startsWith(REPO_ROOT + path.sep)) throw new Error(`${field} must stay inside the project directory`)
  return resolved
}

function positiveInteger(value, field, maximum, allowZero = false) {
  const number = Number(value)
  const minimum = allowZero ? 0 : 1
  if (!Number.isInteger(number) || number < minimum || number > maximum) throw new Error(`${field} must be an integer between ${minimum} and ${maximum}`)
  return number
}

function normalizeDomain(value) {
  if (typeof value !== 'string') throw new Error('allowed domains must be strings')
  const domain = value.trim().toLowerCase()
  if (!domain || domain.includes('/') || domain.includes(':') || domain.includes(' ')) throw new Error(`Invalid allowed domain: ${value}`)
  return domain
}

function domainAllows(hostname, domain) {
  return hostname === domain || hostname.endsWith(`.${domain}`)
}

export function prepareDiscoveryJob(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('job must be an object')
  let startUrl
  try { startUrl = new URL(input.startUrl) } catch { throw new Error('startUrl must be a valid URL') }
  if (!['http:', 'https:'].includes(startUrl.protocol)) throw new Error('startUrl must use http or https')

  const domains = Array.isArray(input.allowedDomains) && input.allowedDomains.length
    ? input.allowedDomains.map(normalizeDomain) : [startUrl.hostname.toLowerCase()]
  if (!domains.some((domain) => domainAllows(startUrl.hostname.toLowerCase(), domain))) throw new Error('startUrl must belong to an allowed domain')

  const outputDir = resolveContained(input.outputDir, 'outputDir')
  let storageState = ''
  if (typeof input.storageState === 'string' && input.storageState.trim()) {
    storageState = resolveContained(input.storageState, 'storageState')
    if (!existsSync(storageState)) throw new Error('storageState file was not found')
  }

  const provider = input.provider === 'heuristic' ? 'heuristic' : 'llama.cpp'
  const endpoint = typeof input.endpoint === 'string' && input.endpoint.trim() ? input.endpoint.trim() : 'http://127.0.0.1:8080/v1/chat/completions'
  if (provider === 'llama.cpp') {
    let endpointUrl
    try { endpointUrl = new URL(endpoint) } catch { throw new Error('endpoint must be a valid URL') }
    if (!['http:', 'https:'].includes(endpointUrl.protocol)) throw new Error('endpoint must use http or https')
    if (!['127.0.0.1', 'localhost', '::1'].includes(endpointUrl.hostname)) throw new Error('endpoint must use a loopback hostname so discovery evidence stays local')
  }
  const model = typeof input.model === 'string' && input.model.trim() ? input.model.trim() : 'qwen3-4b-instruct'

  return {
    manifest: {
      start_url: startUrl.toString(), output_dir: outputDir, allowed_domains: domains,
      max_pages: positiveInteger(input.maxPages ?? 30, 'maxPages', 500),
      max_interactions: positiveInteger(input.maxInteractions ?? 20, 'maxInteractions', 500, true),
      max_depth: positiveInteger(input.maxDepth ?? 4, 'maxDepth', 20, true),
      width: positiveInteger(input.width ?? 1280, 'width', 4096),
      height: positiveInteger(input.height ?? 720, 'height', 4096),
      storage_state: storageState, headless: true,
    },
    provider, endpoint, model, outputDir,
  }
}

function readJson(filePath) {
  return existsSync(filePath) ? JSON.parse(readFileSync(filePath, 'utf8')) : null
}

function resultSummary(outputDir) {
  const snapshot = readJson(path.join(outputDir, 'snapshot.json'))
  if (!snapshot) return null
  const actions = snapshot.actions ?? []
  return {
    schemaVersion: snapshot.schema_version,
    run: snapshot.runs?.at(-1) ?? null,
    counts: {
      pages: snapshot.pages?.length ?? 0, states: snapshot.states?.length ?? 0,
      actions: actions.length, transitions: snapshot.transitions?.length ?? 0,
      findings: snapshot.findings?.length ?? 0, events: snapshot.events?.length ?? 0,
      blockedActions: actions.filter((item) => item.safety === 'blocked').length,
      reviewActions: actions.filter((item) => item.safety === 'review').length,
      unexploredActions: actions.filter((item) => item.status === 'unexplored').length,
      failedEvents: snapshot.events?.filter((item) => item.status === 'failed').length ?? 0,
    },
    pages: (snapshot.pages ?? []).slice(-200).map((item) => ({ id: item.id, title: item.title, url: item.normalized_url })),
    findings: (snapshot.findings ?? []).slice(-100).map((item) => ({
      id: item.id, stateId: item.state_id, evidence: item.evidence, kind: item.kind,
      statement: item.statement, status: item.status, confidence: item.confidence, producer: item.producer,
    })),
    events: (snapshot.events ?? []).slice(-100),
  }
}

function publicRun(run) {
  let progress = null
  try { progress = readJson(path.join(run.outputDir, 'progress.json')) } catch { /* A writer may be replacing the file. */ }
  return {
    runId: run.id,
    status: run.status,
    code: run.code,
    error: run.error,
    stdout: run.stdout,
    stderr: run.stderr,
    manifestPath: path.relative(REPO_ROOT, run.manifestPath),
    snapshotPath: path.relative(REPO_ROOT, path.join(run.outputDir, 'snapshot.json')),
    progress,
    result: run.result,
  }
}

function startRun(prepared) {
  const id = randomUUID()
  const outputDir = path.join(prepared.outputDir, 'runs', id)
  mkdirSync(outputDir, { recursive: true })
  const manifest = { ...prepared.manifest, output_dir: outputDir }
  const manifestPath = path.join(outputDir, 'frontend-discovery.json')
  writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8')
  const args = ['-m', 'pipeline.site_agent.cli', manifestPath, '--provider', prepared.provider]
  if (prepared.provider === 'llama.cpp') args.push('--endpoint', prepared.endpoint, '--model', prepared.model)

  const child = spawn(resolvePythonPath(), args, { cwd: REPO_ROOT, env: process.env, windowsHide: true })
  const run = { id, child, outputDir, manifestPath, status: 'running', code: null, error: null, stdout: '', stderr: '', result: null }
  runs.set(id, run)
  child.stdout.on('data', (chunk) => { if (run.stdout.length < MAX_LOG_CHARS) run.stdout += chunk.toString() })
  child.stderr.on('data', (chunk) => { if (run.stderr.length < MAX_LOG_CHARS) run.stderr += chunk.toString() })
  run.timeout = setTimeout(() => {
    run.status = 'timed_out'
    run.error = 'Discovery timed out'
    child.kill()
  }, RUN_TIMEOUT_MS)
  child.on('close', (code) => {
    clearTimeout(run.timeout)
    run.code = code
    if (run.status === 'running') run.status = code === 0 ? 'completed' : 'failed'
    if (code === 0) {
      try { run.result = resultSummary(outputDir) } catch (error) {
        run.status = 'failed'
        run.error = `Could not read discovery snapshot: ${error.message}`
      }
    } else if (!run.error && run.status !== 'cancelled') {
      run.error = `Discovery exited with code ${code}`
    }
  })
  child.on('error', (error) => {
    clearTimeout(run.timeout)
    run.status = 'failed'
    run.error = `Failed to start process: ${error.message}`
  })
  return run
}

function registerMiddleware(server) {
  server.middlewares.use('/api/run-discovery', (request, response) => {
    if (!isLoopback(request.socket.remoteAddress)) return sendJson(response, 403, { error: 'Forbidden: local requests only' })
    const id = request.url.split('?')[0].split('/').filter(Boolean)[0]
    if (id) {
      const run = runs.get(id)
      if (!run) return sendJson(response, 404, { error: 'Discovery run was not found' })
      if (request.method === 'GET') return sendJson(response, 200, publicRun(run))
      if (request.method === 'DELETE') {
        if (run.status === 'running') {
          run.status = 'cancelled'
          run.error = 'Discovery was stopped by the user'
          clearTimeout(run.timeout)
          run.child.kill()
        }
        return sendJson(response, 200, publicRun(run))
      }
      return sendJson(response, 405, { error: 'Method not allowed' })
    }
    if (request.method !== 'POST') return sendJson(response, 405, { error: 'Method not allowed' })

    let body = ''
    let tooLarge = false
    request.on('data', (chunk) => {
      body += chunk
      if (body.length > MAX_BODY_BYTES) tooLarge = true
    })
    request.on('end', () => {
      if (tooLarge) return sendJson(response, 413, { error: 'Request body is too large' })
      try {
        const run = startRun(prepareDiscoveryJob(JSON.parse(body)))
        sendJson(response, 202, publicRun(run))
      } catch (error) {
        sendJson(response, 400, { error: error instanceof Error ? error.message : 'Invalid request' })
      }
    })
  })
}

export function discoveryRunPlugin() {
  return {
    name: 'mpostele-local-discovery-runner',
    configureServer: registerMiddleware,
    configurePreviewServer: registerMiddleware,
  }
}

