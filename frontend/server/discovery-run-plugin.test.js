import assert from 'node:assert/strict'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { prepareDiscoveryJob, resultSummary, saveReview } from './discovery-run-plugin.js'

const repoRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')

function validJob() {
  return {
    startUrl: 'https://app.example.com/dashboard',
    outputDir: 'artifacts/discovery-test',
    allowedDomains: ['example.com'],
    maxPages: 20,
    maxInteractions: 10,
    maxDepth: 3,
    width: 1280,
    height: 720,
    provider: 'llama.cpp',
    endpoint: 'http://127.0.0.1:8080/v1/chat/completions',
    model: 'qwen3-4b-instruct',
  }
}

test('prepareDiscoveryJob creates a contained Python manifest', () => {
  const prepared = prepareDiscoveryJob(validJob())
  assert.equal(prepared.manifest.output_dir, path.join(repoRoot, 'artifacts', 'discovery-test'))
  assert.deepEqual(prepared.manifest.allowed_domains, ['example.com'])
  assert.equal(prepared.provider, 'llama.cpp')
})

test('prepareDiscoveryJob derives the domain when none is supplied', () => {
  const job = validJob()
  job.allowedDomains = []
  assert.deepEqual(prepareDiscoveryJob(job).manifest.allowed_domains, ['app.example.com'])
})

test('prepareDiscoveryJob rejects a start URL outside the allowed domains', () => {
  const job = validJob()
  job.allowedDomains = ['other.test']
  assert.throws(() => prepareDiscoveryJob(job), /allowed domain/)
})

test('prepareDiscoveryJob rejects output traversal', () => {
  const job = validJob()
  job.outputDir = '../outside'
  assert.throws(() => prepareDiscoveryJob(job), /inside the project/)
})

test('prepareDiscoveryJob rejects non-local model endpoints', () => {
  const job = validJob()
  job.endpoint = 'https://models.example.com/v1/chat/completions'
  assert.throws(() => prepareDiscoveryJob(job), /loopback/)
})

test('prepareDiscoveryJob rejects non-http loopback model endpoints', () => {
  const job = validJob()
  job.endpoint = 'file://localhost/tmp/model'
  assert.throws(() => prepareDiscoveryJob(job), /http or https/)
})

test('prepareDiscoveryJob permits model-free heuristic discovery', () => {
  const job = validJob()
  job.provider = 'heuristic'
  job.endpoint = 'https://unused.example.com'
  assert.equal(prepareDiscoveryJob(job).provider, 'heuristic')
})

test('prepareDiscoveryJob validates crawl budgets', () => {
  const job = validJob()
  job.maxPages = 0
  assert.throws(() => prepareDiscoveryJob(job), /maxPages/)
})

test('resultSummary exposes graph, screenshot, layout, and finding evidence data', () => {
  const outputDir = mkdtempSync(path.join(tmpdir(), 'mpostele-discovery-'))
  try {
    writeFileSync(path.join(outputDir, 'snapshot.json'), JSON.stringify({
      schema_version: '1.1.0',
      pages: [{ id: 'page-1', title: 'Home', normalized_url: 'https://example.com/' }],
      states: [{ id: 'state-1', page_id: 'page-1', observation: { title: 'Home', url: 'https://example.com/', headings: ['Welcome'], visible_text: 'Hello', structure: { heading_outline: [{ level: 1, text: 'Welcome' }], landmarks: [{ type: 'main', label: 'Welcome' }], navigation: [], sections: [], forms: [] }, screenshot_path: 'screenshots/home.png' } }],
      actions: [{ id: 'action-1', state_id: 'state-1', safety: 'review', safety_reason: 'unknown', status: 'unexplored', control: { name: 'Generate' } }],
      transitions: [{ id: 'transition-1', source_state_id: 'state-1', action_id: 'action-1', destination_state_id: 'state-1', status: 'verified', observed_result: 'Changed' }],
      findings: [{ id: 'finding-1', state_id: 'state-1', evidence: ['state-1'], kind: 'purpose', statement: 'Introduces product', status: 'inferred', confidence: 0.7, producer: 'heuristic' }],
      events: [],
      runs: [],
    }))
    const summary = resultSummary(outputDir, 'browser-run')
    assert.equal(summary.states[0].headings[0], 'Welcome')
    assert.equal(summary.states[0].structure.landmarks[0].type, 'main')
    assert.match(summary.states[0].screenshotUrl, /browser-run\/evidence/)
    assert.equal(summary.transitions[0].destinationStateId, 'state-1')
    assert.deepEqual(summary.findings[0].evidence, ['state-1'])
  } finally {
    rmSync(outputDir, { recursive: true, force: true })
  }
})

test('saveReview persists only known review decisions and important graph records', () => {
  const outputDir = mkdtempSync(path.join(tmpdir(), 'mpostele-review-'))
  const run = {
    outputDir,
    result: {
      actions: [{ id: 'action-1', safety: 'review' }],
      pages: [{ id: 'page-1' }],
      transitions: [{ id: 'transition-1' }],
    },
  }
  try {
    const review = saveReview(run, { actions: { 'action-1': 'approved' }, importantPages: ['page-1'], importantTransitions: ['transition-1'] })
    assert.deepEqual(JSON.parse(readFileSync(path.join(outputDir, 'review.json'))), review)
    assert.throws(() => saveReview(run, { actions: { unknown: 'approved' } }), /invalid action/)
  } finally {
    rmSync(outputDir, { recursive: true, force: true })
  }
})
