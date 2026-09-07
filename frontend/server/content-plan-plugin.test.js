import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { convertPlanToManifest, preparePlanningJob, validatePlan, validateScheduledDate } from './content-plan-plugin.js'

const root = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')
const now = new Date(2026, 3, 10, 12)
const scheduled = '2026-04-12'

function plan(snapshot) {
  return {
    schema_version: '1.0.0', scheduled_for: scheduled, status: 'approved',
    source: { snapshot }, brief: { platform: 'shorts', objective: 'Feature tour', audience: 'Teams', target_duration_seconds: 30 },
    scenes: [{
      id: 'scene-01', purpose: 'Show calendar', narration: 'Plan the week in one place.',
      overlay: { type: 'title', text: 'Plan the week' }, estimated_duration_seconds: 4,
      evidence: { state_id: 'state-1', screenshot_path: 'screenshots/calendar.png' },
      confidence: 0.9, review_status: 'approved',
    }],
  }
}

test('seven-day validation includes today through day six only', () => {
  assert.equal(validateScheduledDate('2026-04-16', now), '2026-04-16')
  assert.throws(() => validateScheduledDate('2026-04-17', now), /seven-day/)
})

test('preparePlanningJob contains evidence paths and rejects remote models', () => {
  const directory = path.join(root, 'artifacts', 'content-plan-test')
  mkdirSync(directory, { recursive: true })
  const snapshot = path.join(directory, 'snapshot.json')
  writeFileSync(snapshot, '{}')
  try {
    const prepared = preparePlanningJob({ snapshotPath: path.relative(root, snapshot), outputPath: 'artifacts/content-plan-test/plan.json', scheduledDate: scheduled, objective: 'Tour', audience: 'Teams', tone: 'clear' }, now)
    assert.equal(prepared.provider, 'heuristic')
    assert.equal(prepared.snapshot, snapshot)
    assert.throws(() => preparePlanningJob({ snapshotPath: path.relative(root, snapshot), outputPath: 'artifacts/content-plan-test/plan.json', scheduledDate: scheduled, objective: 'Tour', audience: 'Teams', tone: 'clear', provider: 'llama.cpp', endpoint: 'https://example.com' }, now), /loopback/)
  } finally { rmSync(directory, { recursive: true, force: true }) }
})

test('validatePlan requires evidence and explicit review states', () => {
  const value = plan('snapshot.json')
  assert.equal(validatePlan(value, now), value)
  value.scenes[0].review_status = 'pending'
  assert.throws(() => validatePlan(value, now), /approved plans/)
})

test('approved plans convert to draft image-based render manifests', () => {
  const directory = mkdtempSync(path.join(root, 'artifacts-plan-convert-'))
  const snapshot = path.join(directory, 'snapshot.json')
  const planPath = path.join(directory, 'content-plan.json')
  try {
    const manifest = convertPlanToManifest(plan(snapshot), planPath, { now, videoOutput: path.join(directory, 'video.mp4'), workDir: path.join(directory, 'work') })
    assert.equal(manifest.status, 'draft')
    assert.equal(manifest.export.preset, 'vertical_1080p')
    assert.equal(manifest.scenes[0].script, 'Plan the week in one place.')
    assert.equal(manifest.scenes[0].image, path.join(directory, 'screenshots', 'calendar.png'))
  } finally { rmSync(directory, { recursive: true, force: true }) }
})
