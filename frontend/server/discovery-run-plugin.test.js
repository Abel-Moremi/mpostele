import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { prepareDiscoveryJob } from './discovery-run-plugin.js'

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
