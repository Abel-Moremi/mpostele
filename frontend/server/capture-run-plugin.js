import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// A Vite plugin that adds a local-only HTTP endpoint letting the frontend
// trigger the existing `python -m pipeline.first_render` capture job on this
// machine, instead of the user copy-pasting the generated command into a
// terminal by hand.
//
// This intentionally does NOT introduce a general-purpose remote command
// runner. Security properties that keep it safe as a personal, local tool:
//
// - Loopback only: requests are rejected unless they come from 127.0.0.1/::1,
//   so it stays unreachable even if the dev server is started with --host.
// - No shell: the interpreter is spawned with an argument array
//   (`shell` is never set to true), so shell metacharacters in user input
//   cannot break out into arbitrary shell commands.
// - The password is passed to the child process via an environment variable,
//   never as a CLI argument, so it doesn't appear in process listings
//   (ps / tasklist) and is never written to any log.
// - The output directory is resolved and must stay inside the repository
//   root, which blocks path traversal (e.g. `--output-dir ../../etc`).
const REPO_ROOT = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')
const RUN_TIMEOUT_MS = 3 * 60 * 1000 // capture + render should finish well within 3 minutes
const MAX_BODY_BYTES = 10_000
const MAX_LOG_CHARS = 20_000

function resolvePythonPath() {
  const candidates = [
    path.join(REPO_ROOT, '.venv', 'Scripts', 'python.exe'), // Windows venv
    path.join(REPO_ROOT, '.venv', 'bin', 'python'), // POSIX venv
  ]
  return candidates.find((candidate) => existsSync(candidate)) ?? 'python'
}

function isLoopbackAddress(address) {
  return address === '127.0.0.1' || address === '::1' || address === '::ffff:127.0.0.1'
}

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify(payload))
}

function registerRunCaptureMiddleware(server) {
  const pythonPath = resolvePythonPath()

  server.middlewares.use('/api/run-capture', (req, res) => {
    if (req.method !== 'POST') {
      sendJson(res, 405, { error: 'Method not allowed' })
      return
    }

    if (!isLoopbackAddress(req.socket.remoteAddress)) {
      sendJson(res, 403, { error: 'Forbidden: local requests only' })
      return
    }

    let body = ''
    let tooLarge = false
    req.on('data', (chunk) => {
      body += chunk
      if (body.length > MAX_BODY_BYTES) {
        tooLarge = true
        req.destroy()
      }
    })

    req.on('end', () => {
      if (tooLarge) return

      let job
      try {
        job = JSON.parse(body)
      } catch {
        sendJson(res, 400, { error: 'Invalid JSON body' })
        return
      }

      const { platformUrl, username = '', password = '', targetPath = '', outputDir } = job ?? {}

      let parsedUrl
      try {
        parsedUrl = new URL(platformUrl)
      } catch {
        sendJson(res, 400, { error: 'platformUrl must be a valid URL' })
        return
      }

      if (typeof outputDir !== 'string' || !outputDir.trim()) {
        sendJson(res, 400, { error: 'outputDir is required' })
        return
      }

      const resolvedOutputDir = path.resolve(REPO_ROOT, outputDir)
      if (resolvedOutputDir !== REPO_ROOT && !resolvedOutputDir.startsWith(REPO_ROOT + path.sep)) {
        sendJson(res, 400, { error: 'outputDir must stay inside the project directory' })
        return
      }

      const args = ['-m', 'pipeline.first_render', '--url', parsedUrl.toString(), '--base-dir', outputDir]
      if (typeof username === 'string' && username) args.push('--username', username)
      if (typeof targetPath === 'string' && targetPath) args.push('--target-path', targetPath)

      const child = spawn(pythonPath, args, {
        cwd: REPO_ROOT,
        env: {
          ...process.env,
          ...(typeof password === 'string' && password ? { MPOSTELE_PASSWORD: password } : {}),
        },
        windowsHide: true,
      })

      let stdout = ''
      let stderr = ''
      child.stdout.on('data', (chunk) => {
        if (stdout.length < MAX_LOG_CHARS) stdout += chunk.toString()
      })
      child.stderr.on('data', (chunk) => {
        if (stderr.length < MAX_LOG_CHARS) stderr += chunk.toString()
      })

      const timeout = setTimeout(() => {
        child.kill()
      }, RUN_TIMEOUT_MS)

      child.on('close', (code) => {
        clearTimeout(timeout)
        sendJson(res, 200, { code, stdout, stderr })
      })

      child.on('error', (err) => {
        clearTimeout(timeout)
        sendJson(res, 500, { error: `Failed to start process: ${err.message}` })
      })
    })
  })
}

export function captureRunPlugin() {
  return {
    name: 'mpostele-capture-run',
    configureServer: registerRunCaptureMiddleware,
    configurePreviewServer: registerRunCaptureMiddleware,
  }
}
