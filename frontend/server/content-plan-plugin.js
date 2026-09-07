import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')
const SCHEMA = '1.0.0'
const MAX_BODY = 150_000
const PLATFORMS = new Set(['shorts', 'reels', 'tiktok', 'landscape', 'square'])

function contained(value, field, exists = false) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${field} is required`)
  const result = path.resolve(ROOT, value)
  if (result !== ROOT && !result.startsWith(ROOT + path.sep)) throw new Error(`${field} must stay inside the project directory`)
  if (exists && !existsSync(result)) throw new Error(`${field} was not found`)
  return result
}

function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function validateScheduledDate(value, now = new Date()) {
  const days = new Set(Array.from({ length: 7 }, (_, offset) => dateKey(new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset))))
  if (typeof value !== 'string' || !days.has(value)) throw new Error('scheduledDate must be within the rolling seven-day planning window')
  return value
}

function numberIn(value, field, min, max, integer = false) {
  const number = Number(value)
  if (!Number.isFinite(number) || number < min || number > max || (integer && !Number.isInteger(number))) throw new Error(`${field} must be between ${min} and ${max}`)
  return number
}

export function preparePlanningJob(input, now = new Date()) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('job must be an object')
  const required = (value, field) => {
    if (typeof value !== 'string' || !value.trim()) throw new Error(`${field} is required`)
    return value.trim()
  }
  const provider = input.provider === 'llama.cpp' ? 'llama.cpp' : 'heuristic'
  const endpoint = input.endpoint?.trim() || 'http://127.0.0.1:8080/v1/chat/completions'
  if (provider === 'llama.cpp') {
    let url
    try { url = new URL(endpoint) } catch { throw new Error('endpoint must be a valid URL') }
    if (!['http:', 'https:'].includes(url.protocol) || !['127.0.0.1', 'localhost', '::1'].includes(url.hostname)) throw new Error('endpoint must be an HTTP loopback URL')
  }
  const snapshot = contained(input.snapshotPath, 'snapshotPath', true)
  const review = input.reviewPath?.trim() ? contained(input.reviewPath, 'reviewPath', true) : ''
  const output = contained(input.outputPath, 'outputPath')
  if (output === snapshot || output === review) throw new Error('outputPath cannot overwrite source evidence')
  return {
    snapshot, review, output, provider, endpoint, model: input.model?.trim() || 'qwen3-4b-instruct',
    scheduledDate: validateScheduledDate(input.scheduledDate, now),
    objective: required(input.objective, 'objective'), audience: required(input.audience, 'audience'),
    tone: required(input.tone, 'tone'), callToAction: input.callToAction?.trim() || '',
    platform: PLATFORMS.has(input.platform) ? input.platform : 'shorts',
    duration: numberIn(input.duration ?? 30, 'duration', 5, 300),
    maxScenes: numberIn(input.maxScenes ?? 6, 'maxScenes', 1, 20, true),
    wordsPerMinute: numberIn(input.wordsPerMinute ?? 145, 'wordsPerMinute', 80, 220, true),
  }
}

export function validatePlan(plan, now = new Date()) {
  if (!plan || typeof plan !== 'object' || plan.schema_version !== SCHEMA) throw new Error(`plan schema_version must be ${SCHEMA}`)
  validateScheduledDate(plan.scheduled_for, now)
  if (!['pending_review', 'approved'].includes(plan.status)) throw new Error('plan status is invalid')
  if (!Array.isArray(plan.scenes) || !plan.scenes.length || plan.scenes.length > 20) throw new Error('plan must contain between 1 and 20 scenes')
  const ids = new Set()
  plan.scenes.forEach((scene, index) => {
    if (!scene || typeof scene.id !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(scene.id) || ids.has(scene.id)) throw new Error(`scene ${index + 1} has an invalid or duplicate id`)
    ids.add(scene.id)
    if (!['pending', 'approved', 'rejected'].includes(scene.review_status)) throw new Error(`scene ${index + 1} has an invalid review status`)
    if (typeof scene.narration !== 'string' || !scene.narration.trim()) throw new Error(`scene ${index + 1} narration is required`)
    if (typeof scene.evidence?.screenshot_path !== 'string' || !scene.evidence.screenshot_path.trim()) throw new Error(`scene ${index + 1} requires screenshot evidence`)
    numberIn(scene.estimated_duration_seconds, `scene ${index + 1} duration`, 0.1, 300)
    if (typeof scene.overlay?.text !== 'string') throw new Error(`scene ${index + 1} overlay text is required`)
  })
  if (plan.status === 'approved' && plan.scenes.some((scene) => scene.review_status === 'pending')) throw new Error('approved plans cannot contain pending scenes')
  return plan
}

export function convertPlanToManifest(plan, planPath, options = {}) {
  validatePlan(plan, options.now ?? new Date())
  if (plan.status !== 'approved') throw new Error('approve the plan before creating a draft manifest')
  const scenes = plan.scenes.filter((scene) => scene.review_status === 'approved')
  if (!scenes.length) throw new Error('the plan has no approved scenes')
  const snapshotValue = plan.source?.snapshot
  if (!snapshotValue) throw new Error('plan source snapshot is missing')
  const snapshot = path.isAbsolute(snapshotValue) ? path.resolve(snapshotValue) : path.resolve(path.dirname(planPath), snapshotValue)
  if (!snapshot.startsWith(ROOT + path.sep)) throw new Error('plan source snapshot must stay inside the project directory')
  const presets = { shorts: 'vertical_1080p', reels: 'vertical_1080p', tiktok: 'vertical_1080p', landscape: 'landscape_720p', square: 'square_1080p' }
  return {
    status: 'draft', source_plan: path.relative(ROOT, planPath), scheduled_for: plan.scheduled_for,
    output: contained(options.videoOutput || `outputs/${plan.scheduled_for}-content.mp4`, 'videoOutput'),
    work_dir: contained(options.workDir || `artifacts/render-jobs/${plan.scheduled_for}`, 'workDir'),
    export: { preset: presets[plan.brief?.platform] || 'vertical_1080p', fps: numberIn(options.fps ?? 30, 'fps', 1, 120, true) },
    scenes: scenes.map((scene) => ({
      id: scene.id,
      image: contained(path.resolve(path.dirname(snapshot), scene.evidence.screenshot_path), `scene ${scene.id} screenshot`),
      duration: Number(scene.estimated_duration_seconds), motion_preset: 'zoom_in', script: scene.narration.trim(),
      overlay: { type: scene.overlay.type === 'callout' ? 'callout' : 'title', text: scene.overlay.text.trim() || scene.purpose || scene.id, hold_seconds: 2 },
    })),
  }
}

function pythonPath() {
  return [path.join(ROOT, '.venv', 'Scripts', 'python.exe'), path.join(ROOT, '.venv', 'bin', 'python')].find(existsSync) || 'python'
}
function send(response, status, payload) { response.statusCode = status; response.setHeader('Content-Type', 'application/json'); response.end(JSON.stringify(payload)) }
function local(address) { return ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(address) }
function body(request, response, callback) {
  let text = ''
  request.on('data', (chunk) => { text += chunk })
  request.on('end', () => {
    if (text.length > MAX_BODY) return send(response, 413, { error: 'Request body is too large' })
    try { callback(JSON.parse(text || '{}')) } catch (error) { send(response, 400, { error: error.message }) }
  })
}

function generate(job, response) {
  const args = ['-m', 'pipeline.site_agent.content_plan', job.snapshot, '--output', job.output, '--objective', job.objective, '--audience', job.audience, '--platform', job.platform, '--duration', String(job.duration), '--tone', job.tone, '--call-to-action', job.callToAction, '--max-scenes', String(job.maxScenes), '--words-per-minute', String(job.wordsPerMinute), '--provider', job.provider]
  if (job.review) args.push('--review', job.review)
  if (job.provider === 'llama.cpp') args.push('--endpoint', job.endpoint, '--model', job.model)
  mkdirSync(path.dirname(job.output), { recursive: true })
  const child = spawn(pythonPath(), args, { cwd: ROOT, windowsHide: true })
  let stdout = '', stderr = ''
  child.stdout.on('data', (chunk) => { stdout += chunk.toString() })
  child.stderr.on('data', (chunk) => { stderr += chunk.toString() })
  child.on('close', (code) => {
    if (code !== 0) return send(response, 200, { code, stdout, stderr })
    try {
      const plan = JSON.parse(readFileSync(job.output, 'utf8'))
      plan.scheduled_for = job.scheduledDate
      validatePlan(plan)
      writeFileSync(job.output, JSON.stringify(plan, null, 2), 'utf8')
      send(response, 200, { code, stdout, stderr, planPath: path.relative(ROOT, job.output), plan })
    } catch (error) { send(response, 500, { error: `Could not read generated plan: ${error.message}` }) }
  })
  child.on('error', (error) => send(response, 500, { error: `Failed to start planner: ${error.message}` }))
}

function register(server) {
  server.middlewares.use('/api/content-plans', (request, response) => {
    if (!local(request.socket.remoteAddress)) return send(response, 403, { error: 'Forbidden: local requests only' })
    if (request.method !== 'POST') return send(response, 405, { error: 'Method not allowed' })
    body(request, response, (input) => {
      if (input.action === 'generate') return generate(preparePlanningJob(input.job), response)
      const planPath = contained(input.planPath, 'planPath', input.action === 'load' || input.action === 'convert')
      if (input.action === 'load') return send(response, 200, { planPath: path.relative(ROOT, planPath), plan: JSON.parse(readFileSync(planPath, 'utf8')) })
      if (input.action === 'save') {
        validatePlan(input.plan)
        mkdirSync(path.dirname(planPath), { recursive: true }); writeFileSync(planPath, JSON.stringify(input.plan, null, 2), 'utf8')
        return send(response, 200, { planPath: path.relative(ROOT, planPath), plan: input.plan })
      }
      if (input.action === 'convert') {
        const plan = JSON.parse(readFileSync(planPath, 'utf8'))
        const manifest = convertPlanToManifest(plan, planPath, input.options)
        const manifestPath = contained(input.manifestPath, 'manifestPath')
        mkdirSync(path.dirname(manifestPath), { recursive: true }); writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8')
        return send(response, 200, { manifestPath: path.relative(ROOT, manifestPath), manifest })
      }
      throw new Error('Unknown content-plan action')
    })
  })
}

export function contentPlanPlugin() {
  return { name: 'mpostele-content-plan', configureServer: register, configurePreviewServer: register }
}
