import { createReadStream, existsSync, realpathSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')
const REAL_ROOT = realpathSync(ROOT)
const MIME_TYPES = new Map([
  ['.png', 'image/png'], ['.jpg', 'image/jpeg'], ['.jpeg', 'image/jpeg'], ['.webp', 'image/webp'],
  ['.mp4', 'video/mp4'], ['.webm', 'video/webm'], ['.wav', 'audio/wav'], ['.mp3', 'audio/mpeg'],
])

function local(address) {
  return ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(address)
}

export function resolveLocalMedia(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('file is required')
  const resolved = path.resolve(ROOT, value)
  if (resolved !== ROOT && !resolved.startsWith(ROOT + path.sep)) throw new Error('file must stay inside the project directory')
  if (!existsSync(resolved) || !statSync(resolved).isFile()) throw new Error('file was not found')
  const real = realpathSync(resolved)
  if (!real.startsWith(REAL_ROOT + path.sep)) throw new Error('file must stay inside the project directory')
  if (!MIME_TYPES.has(path.extname(real).toLowerCase())) throw new Error('file type is not supported')
  return real
}

function register(server) {
  server.middlewares.use('/api/local-media', (request, response) => {
    if (!local(request.socket.remoteAddress)) { response.statusCode = 403; return response.end('Forbidden') }
    if (request.method !== 'GET' && request.method !== 'HEAD') { response.statusCode = 405; return response.end('Method not allowed') }
    try {
      const file = resolveLocalMedia(new URL(request.url, 'http://localhost').searchParams.get('file'))
      const size = statSync(file).size
      const type = MIME_TYPES.get(path.extname(file).toLowerCase())
      response.setHeader('Content-Type', type)
      response.setHeader('Accept-Ranges', 'bytes')
      const match = request.headers.range?.match(/^bytes=(\d*)-(\d*)$/)
      let start = 0
      let end = size - 1
      if (match) {
        start = match[1] ? Number(match[1]) : 0
        end = match[2] ? Math.min(Number(match[2]), size - 1) : size - 1
        if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start > end || start >= size) {
          response.statusCode = 416
          response.setHeader('Content-Range', `bytes */${size}`)
          return response.end()
        }
        response.statusCode = 206
        response.setHeader('Content-Range', `bytes ${start}-${end}/${size}`)
      }
      response.setHeader('Content-Length', end - start + 1)
      if (request.method === 'HEAD') return response.end()
      createReadStream(file, { start, end }).pipe(response)
    } catch (error) {
      response.statusCode = error.message === 'file was not found' ? 404 : 400
      response.end(error.message)
    }
  })
}

export function localMediaPlugin() {
  return { name: 'mpostele-local-media', configureServer: register, configurePreviewServer: register }
}
