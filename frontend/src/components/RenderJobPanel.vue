<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getSetting, setSetting } from '../db/sqlite'

const presets = [
  { value: 'vertical_1080p', label: 'Vertical 1080 × 1920' },
  { value: 'landscape_720p', label: 'Landscape 1280 × 720' },
  { value: 'square_1080p', label: 'Square 1080 × 1080' },
]
const motionPresets = ['zoom_in', 'zoom_out', 'pan_left_to_right', 'pan_right_to_left', 'pan_top_to_bottom', 'pan_bottom_to_top', 'static']
let nextSceneNumber = 2

function newScene(id = `scene-${nextSceneNumber++}`) {
  return {
    id,
    sourceType: 'url',
    source: 'http://localhost:5173',
    duration: 4,
    motionPreset: 'zoom_in',
    narrationMode: 'none',
    narration: '',
    script: '',
    ttsVoice: 'af_heart',
    ttsSpeed: 1,
    ttsLangCode: 'a',
    normalizeAudio: true,
    captureMode: 'screenshot',
    username: '',
    targetPath: '',
    selector: '',
    hideSelectors: '',
    motionTrigger: 'hover',
    triggerSelector: '',
    overlayEnabled: false,
    overlayType: 'title',
    overlayText: '',
    overlayHold: 2,
    calloutX: 0,
    calloutY: 0,
  }
}

const job = ref({
  output: 'outputs/product-short.mp4',
  workDir: 'artifacts/product-short',
  preset: 'vertical_1080p',
  fps: 30,
  password: '',
  scenes: [newScene('intro')],
})
const settingsLoaded = ref(false)
const runState = ref('idle')
const runResult = ref(null)
const isRunning = computed(() => runState.value === 'running')

function sceneToManifest(scene) {
  const result = {
    id: scene.id.trim(),
    [scene.sourceType]: scene.source.trim(),
    motion_preset: scene.motionPreset,
  }
  if (scene.duration !== '' && scene.duration !== null) result.duration = Number(scene.duration)
  if (scene.narrationMode === 'file') {
    result.narration = scene.narration.trim()
    result.normalize_audio = scene.normalizeAudio
  } else if (scene.narrationMode === 'script') {
    result.script = scene.script.trim()
    result.tts = {
      voice: scene.ttsVoice.trim(),
      speed: Number(scene.ttsSpeed),
      lang_code: scene.ttsLangCode.trim(),
    }
    result.normalize_audio = scene.normalizeAudio
  }
  if (scene.sourceType === 'url') {
    result.capture = {
      mode: scene.captureMode,
      username: scene.username.trim(),
      target_path: scene.targetPath.trim(),
      selector: scene.selector.trim(),
      hide_selectors: scene.hideSelectors.split('\n').map((value) => value.trim()).filter(Boolean),
    }
    if (scene.captureMode === 'motion') {
      result.capture.motion_trigger = scene.motionTrigger
      result.capture.trigger_selector = scene.triggerSelector.trim()
    }
  }
  if (scene.overlayEnabled) {
    result.overlay = {
      type: scene.overlayType,
      text: scene.overlayText.trim(),
      hold_seconds: Number(scene.overlayHold),
    }
    if (scene.overlayType === 'callout') {
      result.overlay.x = Number(scene.calloutX)
      result.overlay.y = Number(scene.calloutY)
    }
  }
  return result
}

const manifest = computed(() => ({
  output: job.value.output.trim(),
  work_dir: job.value.workDir.trim(),
  export: { preset: job.value.preset, fps: Number(job.value.fps) },
  scenes: job.value.scenes.map(sceneToManifest),
}))
const manifestPreview = computed(() => JSON.stringify(manifest.value, null, 2))
const isValid = computed(() => {
  if (!job.value.output.trim() || !job.value.workDir.trim() || Number(job.value.fps) <= 0) return false
  const ids = job.value.scenes.map((scene) => scene.id.trim())
  if (new Set(ids).size !== ids.length) return false
  return job.value.scenes.length > 0 && job.value.scenes.every((scene) => {
    const idValid = /^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(scene.id.trim())
    let sourceValid = Boolean(scene.source.trim())
    if (sourceValid && scene.sourceType === 'url') {
      try {
        sourceValid = ['http:', 'https:'].includes(new URL(scene.source).protocol)
      } catch {
        sourceValid = false
      }
    }
    const durationValid = scene.duration === '' || scene.duration === null || Number(scene.duration) > 0
    const narrationValid = scene.narrationMode === 'none' ||
      (scene.narrationMode === 'file' && Boolean(scene.narration.trim())) ||
      (scene.narrationMode === 'script' && Boolean(scene.script.trim()) &&
        Boolean(scene.ttsVoice.trim()) && Boolean(scene.ttsLangCode.trim()) && Number(scene.ttsSpeed) > 0)
    return idValid && sourceValid && durationValid && narrationValid &&
      (!scene.overlayEnabled || (scene.overlayText.trim() && Number(scene.overlayHold) > 0))
  })
})

function sourceLabel(scene) {
  return scene.sourceType === 'url' ? 'Page URL' : `${scene.sourceType} path`
}

function addScene() {
  job.value.scenes.push(newScene())
}

function removeScene(index) {
  if (job.value.scenes.length > 1) job.value.scenes.splice(index, 1)
}

function moveScene(index, offset) {
  const target = index + offset
  if (target < 0 || target >= job.value.scenes.length) return
  const [scene] = job.value.scenes.splice(index, 1)
  job.value.scenes.splice(target, 0, scene)
}

function copyManifest() {
  if (isValid.value) navigator.clipboard?.writeText(manifestPreview.value)
}

async function runJob() {
  if (!isValid.value || isRunning.value) return
  runState.value = 'running'
  runResult.value = null
  try {
    const response = await fetch('/api/run-render-job', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manifest: manifest.value, password: job.value.password }),
    })
    const data = await response.json()
    runResult.value = data
    runState.value = response.ok && data.code === 0 ? 'success' : 'error'
  } catch (error) {
    runResult.value = { error: error instanceof Error ? error.message : String(error) }
    runState.value = 'error'
  }
}

onMounted(async () => {
  const stored = await getSetting('renderJob')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      const storedScenes = parsed.scenes?.length
        ? parsed.scenes.map((scene, index) => ({
            ...newScene(scene.id || `scene-${index + 1}`),
            ...scene,
            narrationMode: scene.narrationMode || (scene.narration ? 'file' : 'none'),
          }))
        : job.value.scenes
      Object.assign(job.value, parsed, { password: '', scenes: storedScenes })
      nextSceneNumber = job.value.scenes.length + 1
    } catch {
      // Keep defaults if older local state is malformed.
    }
  }
  settingsLoaded.value = true
})

watch(job, (value) => {
  if (!settingsLoaded.value) return
  const { password, ...persistable } = value
  setSetting('renderJob', JSON.stringify(persistable))
}, { deep: true })
</script>

<template>
  <section id="render" class="capture-panel section-card">
    <div class="section-head render-heading">
      <div>
        <p class="eyebrow">Multi-scene export</p>
        <h2>Build and render a complete video</h2>
      </div>
      <button class="secondary-btn" type="button" @click="addScene">Add scene</button>
    </div>

    <div class="form-grid">
      <label>Final output path<input v-model="job.output" type="text" /></label>
      <label>Intermediate work folder<input v-model="job.workDir" type="text" /></label>
      <label>Export preset
        <select v-model="job.preset"><option v-for="preset in presets" :key="preset.value" :value="preset.value">{{ preset.label }}</option></select>
      </label>
      <label>Frames per second<input v-model.number="job.fps" type="number" min="1" step="1" /></label>
      <label>Login password (optional, never saved)<input v-model="job.password" type="password" autocomplete="new-password" /></label>
    </div>

    <div class="scene-list">
      <article v-for="(scene, index) in job.scenes" :key="scene.id + index" class="scene-editor">
        <div class="scene-toolbar">
          <strong>Scene {{ index + 1 }}</strong>
          <div class="scene-actions">
            <button type="button" :disabled="index === 0" @click="moveScene(index, -1)">Move up</button>
            <button type="button" :disabled="index === job.scenes.length - 1" @click="moveScene(index, 1)">Move down</button>
            <button type="button" :disabled="job.scenes.length === 1" @click="removeScene(index)">Remove</button>
          </div>
        </div>

        <div class="form-grid scene-grid">
          <label>Scene ID<input v-model="scene.id" type="text" pattern="[A-Za-z0-9_-]+" /></label>
          <label>Source type
            <select v-model="scene.sourceType"><option value="url">URL</option><option value="image">Image</option><option value="video">Video</option></select>
          </label>
          <label class="wide-field">{{ sourceLabel(scene) }}<input v-model="scene.source" type="text" /></label>
          <label>Duration (seconds, optional)<input v-model.number="scene.duration" type="number" min="0.1" step="0.1" /></label>
          <label>Motion preset
            <select v-model="scene.motionPreset"><option v-for="preset in motionPresets" :key="preset" :value="preset">{{ preset }}</option></select>
          </label>
          <label>Narration
            <select v-model="scene.narrationMode">
              <option value="none">None</option>
              <option value="file">Local audio file</option>
              <option value="script">Generate from script</option>
            </select>
          </label>
          <label v-if="scene.narrationMode === 'file'">Narration path<input v-model="scene.narration" type="text" placeholder="assets/voiceover.wav" /></label>
          <label v-if="scene.narrationMode !== 'none'" class="inline-checkbox"><input v-model="scene.normalizeAudio" type="checkbox" /> Normalize narration</label>
        </div>

        <fieldset v-if="scene.narrationMode === 'script'" class="scene-options">
          <legend>Local text to speech</legend>
          <div class="form-grid scene-grid">
            <label class="wide-field">Narration script<textarea v-model="scene.script" rows="4" placeholder="Describe this scene clearly and briefly."></textarea></label>
            <label>Kokoro voice<input v-model="scene.ttsVoice" type="text" placeholder="af_heart" /></label>
            <label>Speech speed<input v-model.number="scene.ttsSpeed" type="number" min="0.1" step="0.05" /></label>
            <label>Language code<input v-model="scene.ttsLangCode" type="text" placeholder="a" /></label>
          </div>
          <p class="run-hint">Requires the optional dependencies in requirements-tts.txt. Generated audio is cached in the scene work folder.</p>
        </fieldset>

        <fieldset v-if="scene.sourceType === 'url'" class="scene-options">
          <legend>Browser capture</legend>
          <div class="form-grid scene-grid">
            <label>Capture mode<select v-model="scene.captureMode"><option value="screenshot">Screenshot</option><option value="motion">Live motion</option></select></label>
            <label>Username<input v-model="scene.username" type="text" /></label>
            <label>Target path<input v-model="scene.targetPath" type="text" placeholder="/dashboard" /></label>
            <label>Capture selector<input v-model="scene.selector" type="text" placeholder="#app" /></label>
            <label v-if="scene.captureMode === 'motion'">Motion trigger<select v-model="scene.motionTrigger"><option value="hover">Hover</option><option value="click">Click</option><option value="scroll">Scroll</option><option value="none">None</option></select></label>
            <label v-if="scene.captureMode === 'motion'">Trigger selector<input v-model="scene.triggerSelector" type="text" /></label>
            <label class="wide-field">Selectors to hide (one per line)<textarea v-model="scene.hideSelectors" rows="2"></textarea></label>
          </div>
        </fieldset>

        <fieldset class="scene-options">
          <legend><label class="legend-toggle"><input v-model="scene.overlayEnabled" type="checkbox" /> Add overlay</label></legend>
          <div v-if="scene.overlayEnabled" class="form-grid scene-grid">
            <label>Overlay type<select v-model="scene.overlayType"><option value="title">Title</option><option value="callout">Callout</option></select></label>
            <label>Overlay text<input v-model="scene.overlayText" type="text" /></label>
            <label>Hold seconds<input v-model.number="scene.overlayHold" type="number" min="0.1" step="0.1" /></label>
            <template v-if="scene.overlayType === 'callout'">
              <label>Callout X<input v-model.number="scene.calloutX" type="number" step="0.1" /></label>
              <label>Callout Y<input v-model.number="scene.calloutY" type="number" step="0.1" /></label>
            </template>
          </div>
        </fieldset>
      </article>
    </div>

    <div v-if="!isValid" class="field-error render-error">Complete all required paths, narration settings, and valid scene IDs; durations and enabled overlays must be valid.</div>
    <details class="manifest-preview"><summary>Preview generated manifest</summary><pre>{{ manifestPreview }}</pre></details>

    <div class="run-actions">
      <button class="primary-btn" type="button" :disabled="!isValid || isRunning" @click="runJob">{{ isRunning ? 'Rendering…' : 'Render complete video' }}</button>
      <button class="secondary-btn" type="button" :disabled="!isValid" @click="copyManifest">Copy manifest JSON</button>
      <p class="run-hint">Runs locally. Intermediate scene files remain in the configured work folder.</p>
    </div>

    <div v-if="runResult" class="run-status" :class="runState">
      <p class="run-status-title">
        <template v-if="runState === 'success'">Video created at {{ runResult.outputPath }}.</template>
        <template v-else-if="runResult.error">Failed to run: {{ runResult.error }}</template>
        <template v-else>Process exited with code {{ runResult.code }}.</template>
      </p>
      <pre v-if="runResult.manifestPath" class="run-log">Saved manifest: {{ runResult.manifestPath }}</pre>
      <pre v-if="runResult.stdout" class="run-log">{{ runResult.stdout }}</pre>
      <pre v-if="runResult.stderr" class="run-log run-log-error">{{ runResult.stderr }}</pre>
    </div>
  </section>
</template>
