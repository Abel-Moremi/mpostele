import assert from 'node:assert/strict'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { resolveLocalMedia } from './local-media-plugin.js'

const root = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..', '..')

test('local media resolver serves supported project files only', () => {
  const directory = path.join(root, 'artifacts', 'local-media-test')
  const image = path.join(directory, 'frame.png')
  mkdirSync(directory, { recursive: true })
  writeFileSync(image, 'png')
  try {
    assert.equal(resolveLocalMedia('artifacts/local-media-test/frame.png'), image)
    assert.throws(() => resolveLocalMedia('../outside.png'), /inside the project/)
    assert.throws(() => resolveLocalMedia('README.md'), /not supported/)
    assert.throws(() => resolveLocalMedia('artifacts/local-media-test/missing.png'), /not found/)
  } finally {
    rmSync(directory, { recursive: true, force: true })
  }
})
