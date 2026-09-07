<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getSetting, setSetting } from '../db/sqlite'

const settingsLoaded = ref(false)
const runState = ref('idle')
const runResult = ref(null)
let pollTimer = null
const viewportPresets = {
  desktop: { width: 1280, height: 720 },
  mobile: { width: 390, height: 844 },
}
const job = ref({
  startUrl: 'http://localhost:5173',
  outputDir: 'artifacts/site-analysis/local-frontend',
  allowedDomains: 'localhost',
  maxPages: 20,
  maxInteractions: 10,
  maxDepth: 3,
  width: 1280,
  height: 720,
  storageState: '',
  provider: 'llama.cpp',
  endpoint: 'http://127.0.0.1:8080/v1/chat/completions',
  model: 'qwen3-4b-instruct',
})

const isRunning = computed(() => runState.value === 'running')
const parsedDomains = computed(() => job.value.allowedDomains.split(',').map((value) => value.trim()).filter(Boolean))
const isUrlValid = computed(() => {
  try { return ['http:', 'https:'].includes(new URL(job.value.startUrl).protocol) } catch { return false }
})
const isValid = computed(() => isUrlValid.value && Boolean(job.value.outputDir.trim()) &&
  Number.isInteger(Number(job.value.maxPages)) && Number(job.value.maxPages) > 0 &&
  Number.isInteger(Number(job.value.maxInteractions)) && Number(job.value.maxInteractions) >= 0 &&
  Number.isInteger(Number(job.value.maxDepth)) && Number(job.value.maxDepth) >= 0 &&
  Number(job.value.width) > 0 && Number(job.value.height) > 0 &&
  (job.value.provider === 'heuristic' || (job.value.endpoint.trim() && job.value.model.trim())))
const requestPayload = computed(() => ({
  ...job.value,
  allowedDomains: parsedDomains.value,
  maxPages: Number(job.value.maxPages),
  maxInteractions: Number(job.value.maxInteractions),
  maxDepth: Number(job.value.maxDepth),
  width: Number(job.value.width),
  height: Number(job.value.height),
}))
const command = computed(() => {
  const provider = job.value.provider === 'heuristic' ? 'heuristic' : 'llama.cpp'
  return `python -m pipeline.site_agent.cli ${job.value.outputDir}/runs/<run-id>/frontend-discovery.json --provider ${provider}`
})
const result = computed(() => runResult.value?.result ?? null)
const progress = computed(() => runResult.value?.progress ?? null)

function applyViewport(preset) {
  Object.assign(job.value, viewportPresets[preset])
}

async function pollRun(runId) {
  try {
    const response = await fetch(`/api/run-discovery/${runId}`)
    const data = await response.json()
    runResult.value = data
    if (data.status === 'running') {
      pollTimer = window.setTimeout(() => pollRun(runId), 750)
    } else {
      runState.value = data.status === 'completed' ? 'success' : 'error'
    }
  } catch (error) {
    runResult.value = { error: error instanceof Error ? error.message : String(error) }
    runState.value = 'error'
  }
}

async function runDiscovery() {
  if (!isValid.value || isRunning.value) return
  runState.value = 'running'
  runResult.value = null
  try {
    const response = await fetch('/api/run-discovery', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestPayload.value),
    })
    const data = await response.json()
    runResult.value = data
    if (!response.ok || !data.runId) {
      runState.value = 'error'
      return
    }
    await pollRun(data.runId)
  } catch (error) {
    runResult.value = { error: error instanceof Error ? error.message : String(error) }
    runState.value = 'error'
  }
}

async function stopDiscovery() {
  if (!runResult.value?.runId || !isRunning.value) return
  if (pollTimer) window.clearTimeout(pollTimer)
  const response = await fetch(`/api/run-discovery/${runResult.value.runId}`, { method: 'DELETE' })
  runResult.value = await response.json()
  runState.value = 'error'
}

function confidenceLabel(value) {
  return `${Math.round(Number(value) * 100)}%`
}

onMounted(async () => {
  const stored = await getSetting('discoveryJob')
  if (stored) {
    try { Object.assign(job.value, JSON.parse(stored)) } catch { /* Keep safe defaults. */ }
  }
  settingsLoaded.value = true
})

watch(job, (value) => {
  if (settingsLoaded.value) setSetting('discoveryJob', JSON.stringify(value))
}, { deep: true })

onUnmounted(() => {
  if (pollTimer) window.clearTimeout(pollTimer)
})
</script>

<template>
  <section id="discovery" class="capture-panel section-card discovery-panel">
    <div class="section-head discovery-heading">
      <div>
        <p class="eyebrow">Site understanding agent</p>
        <h2>Discover the product before planning a recording</h2>
        <p class="section-description">Build an evidence-backed map of pages, interface states, controls, transitions, and inferred purposes. Unknown or consequential controls are not clicked.</p>
      </div>
      <span class="local-badge">Local only</span>
    </div>

    <div class="form-grid">
      <label class="wide-field">Starting URL
        <input v-model.trim="job.startUrl" type="url" placeholder="https://app.example.com" :aria-invalid="!isUrlValid" />
        <span v-if="!isUrlValid" class="field-error">Use an HTTP or HTTPS URL.</span>
      </label>
      <label>Allowed domains
        <input v-model="job.allowedDomains" type="text" placeholder="example.com, app.example.com" />
        <span class="field-help">Comma separated. Leave empty to use the starting hostname.</span>
      </label>
      <label>Evidence output folder
        <input v-model.trim="job.outputDir" type="text" placeholder="artifacts/site-analysis/product" />
      </label>
      <label>Reasoning provider
        <select v-model="job.provider">
          <option value="llama.cpp">Qwen via local llama.cpp</option>
          <option value="heuristic">Heuristic — no LLM</option>
        </select>
      </label>
      <label>Playwright storage state (optional)
        <input v-model.trim="job.storageState" type="text" placeholder="artifacts/auth/state.json" />
        <span class="field-help">For an existing authenticated browser session. Keep this file private.</span>
      </label>
    </div>

    <fieldset v-if="job.provider === 'llama.cpp'" class="scene-options discovery-options">
      <legend>Local model</legend>
      <div class="form-grid scene-grid">
        <label>llama.cpp endpoint<input v-model.trim="job.endpoint" type="url" /></label>
        <label>Model name<input v-model.trim="job.model" type="text" /></label>
      </div>
      <p class="run-hint">The server endpoint must be loopback-only. If a model request fails, that state falls back to deterministic analysis.</p>
    </fieldset>

    <fieldset class="scene-options discovery-options">
      <legend>Exploration budget</legend>
      <div class="viewport-presets" aria-label="Viewport presets">
        <button class="secondary-btn" type="button" @click="applyViewport('desktop')">Desktop 1280 × 720</button>
        <button class="secondary-btn" type="button" @click="applyViewport('mobile')">Mobile 390 × 844</button>
      </div>
      <div class="discovery-budget-grid">
        <label>Maximum pages<input v-model.number="job.maxPages" type="number" min="1" max="500" /></label>
        <label>Safe interactions<input v-model.number="job.maxInteractions" type="number" min="0" max="500" /></label>
        <label>Link depth<input v-model.number="job.maxDepth" type="number" min="0" max="20" /></label>
        <label>Viewport width<input v-model.number="job.width" type="number" min="320" max="4096" /></label>
        <label>Viewport height<input v-model.number="job.height" type="number" min="320" max="4096" /></label>
      </div>
    </fieldset>

    <div class="command-box"><pre>{{ command }}</pre></div>
    <div v-if="!isValid" class="field-error render-error">Complete the URL, output, model, and exploration limits before running discovery.</div>

    <div class="run-actions">
      <button class="primary-btn" type="button" :disabled="!isValid || isRunning" @click="runDiscovery">
        {{ isRunning ? 'Discovering site…' : 'Run discovery agent' }}
      </button>
      <button v-if="isRunning" class="secondary-btn" type="button" @click="stopDiscovery">Stop run</button>
      <p class="run-hint">Discovery can take several minutes. The browser and reasoning model run sequentially to keep memory use modest.</p>
    </div>

    <div v-if="isRunning && progress" class="discovery-progress" aria-live="polite">
      <div><strong>Current page</strong><span>{{ progress.current_url || 'Starting browser…' }}</span></div>
      <div class="progress-counts">
        <span>{{ progress.pages }} pages</span><span>{{ progress.states }} states</span>
        <span>{{ progress.actions }} actions</span><span>{{ progress.transitions }} transitions</span>
      </div>
      <p v-if="progress.fallback_count" class="field-error">Local model fallback used for {{ progress.fallback_count }} state(s).</p>
    </div>

    <div v-if="runResult && !isRunning" class="run-status" :class="runState">
      <p class="run-status-title">
        <template v-if="runState === 'success'">Discovery completed. Knowledge saved to {{ runResult.snapshotPath }}.</template>
        <template v-else-if="runResult.error">{{ runResult.error }}</template>
        <template v-else>Discovery exited with code {{ runResult.code }}.</template>
      </p>
      <pre v-if="runResult.stderr" class="run-log run-log-error">{{ runResult.stderr }}</pre>
    </div>

    <div v-if="result" class="discovery-results">
      <div class="result-heading">
        <div><p class="eyebrow">Knowledge snapshot</p><h3>Discovery results</h3></div>
        <span class="schema-badge">Schema {{ result.schemaVersion }}</span>
      </div>

      <div class="metric-grid">
        <article><strong>{{ result.counts.pages }}</strong><span>Pages</span></article>
        <article><strong>{{ result.counts.states }}</strong><span>UI states</span></article>
        <article><strong>{{ result.counts.actions }}</strong><span>Actions</span></article>
        <article><strong>{{ result.counts.transitions }}</strong><span>Transitions</span></article>
        <article><strong>{{ result.counts.findings }}</strong><span>Findings</span></article>
        <article><strong>{{ result.counts.blockedActions }}</strong><span>Blocked</span></article>
        <article><strong>{{ result.counts.reviewActions }}</strong><span>Need review</span></article>
        <article><strong>{{ result.counts.unexploredActions }}</strong><span>Unexplored</span></article>
        <article><strong>{{ result.counts.failedEvents }}</strong><span>Failed events</span></article>
        <article><strong>{{ result.counts.events }}</strong><span>All events</span></article>
      </div>
      <p v-if="runResult.progress?.fallback_count" class="fallback-status">Heuristic fallback analyzed {{ runResult.progress.fallback_count }} state(s) after local model errors.</p>

      <div class="result-columns">
        <section class="result-list">
          <div class="result-list-head"><h4>Pages</h4><span>{{ result.pages.length }} shown</span></div>
          <ul v-if="result.pages.length">
            <li v-for="page in result.pages" :key="page.id">
              <strong>{{ page.title || 'Untitled page' }}</strong>
              <a :href="page.url" target="_blank" rel="noreferrer">{{ page.url }}</a>
            </li>
          </ul>
          <p v-else class="empty-result">No pages were stored.</p>
        </section>

        <section class="result-list">
          <div class="result-list-head"><h4>Inferred findings</h4><span>{{ result.findings.length }} shown</span></div>
          <ul v-if="result.findings.length">
            <li v-for="finding in result.findings" :key="finding.id">
              <div class="finding-meta"><span>{{ finding.kind.replaceAll('_', ' ') }}</span><span>{{ confidenceLabel(finding.confidence) }}</span></div>
              <strong>{{ finding.statement }}</strong>
              <small>{{ finding.status }} · {{ finding.producer }} · evidence: {{ finding.evidence?.join(', ') || finding.stateId }}</small>
            </li>
          </ul>
          <p v-else class="empty-result">No interpretations were produced.</p>
        </section>
      </div>

      <details v-if="result.events.length" class="manifest-preview">
        <summary>Run events and failures ({{ result.events.length }})</summary>
        <pre>{{ JSON.stringify(result.events, null, 2) }}</pre>
      </details>
    </div>
  </section>
</template>
