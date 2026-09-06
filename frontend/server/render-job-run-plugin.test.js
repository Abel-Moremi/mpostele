import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { prepareManifest } from './render-job-run-plugin.js'

const repoRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')

function validJob() {
  return {
    output: 'outputs/test.mp4',
    work_dir: 'artifacts/test-job',
    export: { preset: 'vertical_1080p', fps: 30 },
    scenes: [{ id: 'intro', video: 'README.md', duration: 1 }],
  }
}

test('prepareManifest resolves project paths for the Python job', () => {
  const prepared = prepareManifest(validJob())
  assert.equal(prepared.output, path.join(repoRoot, 'outputs', 'test.mp4'))
  assert.equal(prepared.work_dir, path.join(repoRoot, 'artifacts', 'test-job'))
  assert.equal(prepared.scenes[0].video, path.join(repoRoot, 'README.md'))
})

test('prepareManifest rejects output path traversal', () => {
  const job = validJob()
  job.output = '../outside.mp4'
  assert.throws(() => prepareManifest(job), /must stay inside/)
})

test('prepareManifest rejects non-http page URLs', () => {
  const job = validJob()
  job.scenes = [{ id: 'intro', url: 'file:///private/page.html', duration: 1 }]
  assert.throws(() => prepareManifest(job), /must use http or https/)
})

test('prepareManifest requires existing local source files', () => {
  const job = validJob()
  job.scenes[0].video = 'missing-video.mp4'
  assert.throws(() => prepareManifest(job), /source file was not found/)
})

test('prepareManifest accepts a script with default TTS settings', () => {
  const job = validJob()
  job.scenes[0].script = 'Use the defaults.'
  assert.equal(prepareManifest(job).scenes[0].script, 'Use the defaults.')
})

test('prepareManifest accepts local TTS script settings', () => {
  const job = validJob()
  Object.assign(job.scenes[0], {
    script: 'A locally generated voiceover.',
    tts: { voice: 'af_heart', speed: 1, lang_code: 'a' },
  })
  const prepared = prepareManifest(job)
  assert.equal(prepared.scenes[0].script, 'A locally generated voiceover.')
  assert.equal(prepared.scenes[0].tts.voice, 'af_heart')
})

test('prepareManifest rejects narration and script together', () => {
  const job = validJob()
  Object.assign(job.scenes[0], {
    narration: 'README.md',
    script: 'This conflicts with the narration file.',
    tts: { voice: 'af_heart', speed: 1, lang_code: 'a' },
  })
  assert.throws(() => prepareManifest(job), /cannot define both/)
})
