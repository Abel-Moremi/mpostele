<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { getSetting, setSetting } from '../db/sqlite'

const emit = defineEmits(['status', 'use-in-plan'])
const settingsLoaded = ref(false)
const runState = ref('idle')
const runResult = ref(null)
const selectedStateId = ref('')
const reviewSaving = ref(false)
const reviewMessage = ref('')
let pollTimer = null
let elapsedTimer = null
const elapsedSeconds = ref(0)
const elapsedLabel = computed(() => `${Math.floor(elapsedSeconds.value / 60)}m ${String(elapsedSeconds.value % 60).padStart(2, '0')}s`)
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
const selectedState = computed(() => result.value?.states.find((state) => state.id === selectedStateId.value) ?? result.value?.states[0] ?? null)
const selectedActions = computed(() => result.value?.actions.filter((action) => action.stateId === selectedState.value?.id) ?? [])
const reviewActions = computed(() => result.value?.actions.filter((action) => action.safety === 'review') ?? [])
const graphNodes = computed(() => (result.value?.states ?? []).slice(0, 40).map((state, index) => ({
  ...state,
  x: 115 + (index % 4) * 220,
  y: 55 + Math.floor(index / 4) * 105,
})))
const graphEdges = computed(() => {
  const positions = new Map(graphNodes.value.map((node) => [node.id, node]))
  return (result.value?.transitions ?? []).filter((edge) => positions.has(edge.sourceStateId) && positions.has(edge.destinationStateId)).map((edge) => ({
    ...edge,
    source: positions.get(edge.sourceStateId),
    destination: positions.get(edge.destinationStateId),
  }))
})
const graphHeight = computed(() => Math.max(150, Math.ceil(graphNodes.value.length / 4) * 105))

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
      runState.value = data.status === 'completed' ? 'success' : data.status === 'stopped' ? 'stopped' : 'error'
      emit('status', runState.value === 'success' ? 'completed' : runState.value)
      if (elapsedTimer) window.clearInterval(elapsedTimer)
      if (data.status === 'completed' && data.result?.states?.length) selectedStateId.value = data.result.states[0].id
    }
  } catch (error) {
    runResult.value = { error: error instanceof Error ? error.message : String(error) }
    runState.value = 'error'
    emit('status', 'failed')
    if (elapsedTimer) window.clearInterval(elapsedTimer)
  }
}

async function runDiscovery() {
  if (!isValid.value || isRunning.value) return
  runState.value = 'running'
  emit('status', 'running')
  elapsedSeconds.value = 0
  if (elapsedTimer) window.clearInterval(elapsedTimer)
  elapsedTimer = window.setInterval(() => { elapsedSeconds.value += 1 }, 1000)
  runResult.value = null
  selectedStateId.value = ''
  reviewMessage.value = ''
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
      emit('status', 'failed')
      if (elapsedTimer) window.clearInterval(elapsedTimer)
      return
    }
    await pollRun(data.runId)
  } catch (error) {
    runResult.value = { error: error instanceof Error ? error.message : String(error) }
    runState.value = 'error'
    emit('status', 'failed')
    if (elapsedTimer) window.clearInterval(elapsedTimer)
  }
}

async function stopDiscovery() {
  if (!runResult.value?.runId || !isRunning.value) return
  if (pollTimer) window.clearTimeout(pollTimer)
  const response = await fetch(`/api/run-discovery/${runResult.value.runId}`, { method: 'DELETE' })
  runResult.value = await response.json()
  runState.value = 'stopped'
  emit('status', 'stopped')
  if (elapsedTimer) window.clearInterval(elapsedTimer)
}

async function saveReview(nextReview) {
  if (!runResult.value?.runId) return
  reviewSaving.value = true
  reviewMessage.value = ''
  try {
    const response = await fetch(`/api/run-discovery/${runResult.value.runId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nextReview),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || 'Could not save review')
    runResult.value.review = data.review
    reviewMessage.value = 'Review saved locally.'
  } catch (error) {
    reviewMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    reviewSaving.value = false
  }
}

function reviewPayload(overrides = {}) {
  return {
    actions: { ...(runResult.value?.review?.actions ?? {}) },
    importantPages: [...(runResult.value?.review?.importantPages ?? [])],
    importantTransitions: [...(runResult.value?.review?.importantTransitions ?? [])],
    ...overrides,
  }
}

function decideAction(actionId, decision) {
  const actions = { ...(runResult.value?.review?.actions ?? {}) }
  if (actions[actionId] === decision) delete actions[actionId]
  else actions[actionId] = decision
  saveReview(reviewPayload({ actions }))
}

function toggleImportant(kind, id) {
  const key = kind === 'page' ? 'importantPages' : 'importantTransitions'
  const values = new Set(runResult.value?.review?.[key] ?? [])
  if (values.has(id)) values.delete(id)
  else values.add(id)
  saveReview(reviewPayload({ [key]: [...values] }))
}

function isImportant(kind, id) {
  const key = kind === 'page' ? 'importantPages' : 'importantTransitions'
  return runResult.value?.review?.[key]?.includes(id)
}

function showFindingEvidence(finding) {
  selectedStateId.value = finding.evidence?.[0] ?? finding.stateId
  document.querySelector('.evidence-browser')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function exploreFrom(page) {
  job.value.startUrl = page.url
  runDiscovery()
}

function shortLabel(value, length = 28) {
  if (!value) return 'Untitled state'
  return value.length > length ? `${value.slice(0, length)}…` : value
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
  if (elapsedTimer) window.clearInterval(elapsedTimer)
})
</script>

<template>
  <section id="discovery" class="capture-panel section-card discovery-panel">
    <div class="section-head discovery-heading">
      <div>
        <p class="eyebrow">Site understanding agent</p>
        <h2>Discover the product before planning a recording</h2>
        <p class="section-description">Build an evidence-backed map of the website structure, pages, interface states, controls, transitions, and inferred purposes. Unknown or consequential controls are not clicked.</p>
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

    <details class="advanced-settings">
      <summary>Advanced settings <span>{{ job.width }} × {{ job.height }} · {{ job.maxPages }} pages · {{ job.maxInteractions }} safe actions</span></summary>
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

    <details class="manifest-preview technical-details"><summary>Technical command</summary><div class="command-box"><pre>{{ command }}</pre></div></details>
    </details>
    <div v-if="!isValid" class="field-error render-error">Complete the URL, output, model, and exploration limits before running discovery.</div>

    <div class="run-actions">
      <button class="primary-btn" type="button" :disabled="!isValid || isRunning" @click="runDiscovery">
        {{ isRunning ? 'Discovering site…' : 'Run discovery agent' }}
      </button>
      <button v-if="isRunning" class="secondary-btn" type="button" @click="stopDiscovery">Stop run</button>
      <p class="run-hint">Discovery can take several minutes. The browser and reasoning model run sequentially to keep memory use modest.</p>
    </div>

    <div v-if="isRunning && progress" class="discovery-progress" aria-live="polite">
      <div><strong>Current stage · {{ elapsedLabel }}</strong><span>{{ progress.current_url || 'Starting browser…' }}</span></div>
      <div class="progress-counts">
        <span>{{ progress.pages }} pages</span><span>{{ progress.states }} states</span>
        <span>{{ progress.actions }} actions</span><span>{{ progress.transitions }} transitions</span>
      </div>
      <p v-if="progress.fallback_count" class="field-error">Local model fallback used for {{ progress.fallback_count }} state(s).</p>
    </div>

    <div v-if="runResult && !isRunning" class="run-status" :class="runState">
      <p class="run-status-title">
        <template v-if="runState === 'success'">Discovery completed in {{ elapsedLabel }}. Knowledge saved to {{ runResult.snapshotPath }}.</template>
        <template v-else-if="runState === 'stopped'">Discovery stopped after {{ elapsedLabel }}. Partial run files remain available locally.</template>
        <template v-else-if="runResult.error">{{ runResult.error }}</template>
        <template v-else>Discovery exited with code {{ runResult.code }}.</template>
      </p>
      <pre v-if="runResult.stderr" class="run-log run-log-error">{{ runResult.stderr }}</pre>
    </div>

    <div v-if="result" class="discovery-results">
      <div class="result-heading">
        <div><p class="eyebrow">Knowledge snapshot</p><h3>Discovery results</h3></div>
        <div class="heading-actions"><span class="schema-badge">Schema {{ result.schemaVersion }}</span><button class="primary-btn" type="button" @click="emit('use-in-plan', runResult.snapshotPath)">Use this discovery in Plan</button></div>
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
      <p v-if="reviewMessage" class="review-status" aria-live="polite">{{ reviewMessage }}</p>

      <div class="result-columns">
        <section class="result-list">
          <div class="result-list-head"><h4>Pages</h4><span>{{ result.pages.length }} shown</span></div>
          <ul v-if="result.pages.length">
            <li v-for="page in result.pages" :key="page.id">
              <div class="inventory-title">
                <strong>{{ page.title || 'Untitled page' }}</strong>
                <button class="icon-btn" type="button" :aria-pressed="isImportant('page', page.id)" :title="isImportant('page', page.id) ? 'Remove important marker' : 'Mark important page'" :disabled="reviewSaving" @click="toggleImportant('page', page.id)">{{ isImportant('page', page.id) ? 'Important' : 'Mark important' }}</button>
              </div>
              <a :href="page.url" target="_blank" rel="noreferrer">{{ page.url }}</a>
              <button class="text-btn" type="button" @click="exploreFrom(page)">Explore from this page</button>
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
              <button class="text-btn" type="button" @click="showFindingEvidence(finding)">View evidence</button>
            </li>
          </ul>
          <p v-else class="empty-result">No interpretations were produced.</p>
        </section>
      </div>

      <section class="discovery-detail">
        <div class="result-list-head"><h4>Site and flow graph</h4><span>{{ graphNodes.length }} states · {{ graphEdges.length }} visible transitions</span></div>
        <div class="graph-scroll">
          <svg class="flow-graph" width="900" :height="graphHeight" role="img" aria-label="Discovered state transition graph">
            <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" /></marker></defs>
            <line v-for="edge in graphEdges" :key="edge.id" :x1="edge.source.x" :y1="edge.source.y" :x2="edge.destination.x" :y2="edge.destination.y" :class="{ important: isImportant('transition', edge.id) }" marker-end="url(#arrow)" />
            <g v-for="node in graphNodes" :key="node.id" class="graph-node" :class="{ selected: selectedState?.id === node.id, important: isImportant('page', node.pageId) }" role="button" tabindex="0" @click="selectedStateId = node.id" @keydown.enter="selectedStateId = node.id">
              <rect :x="node.x - 88" :y="node.y - 25" width="176" height="50" rx="12" />
              <text :x="node.x" :y="node.y - 3">{{ shortLabel(node.title) }}</text>
              <text class="node-subtitle" :x="node.x" :y="node.y + 14">{{ shortLabel(node.url, 32) }}</text>
            </g>
          </svg>
        </div>
        <ul v-if="result.transitions.length" class="transition-list">
          <li v-for="edge in result.transitions" :key="edge.id">
            <span>{{ shortLabel(edge.sourceStateId, 18) }} → {{ shortLabel(edge.destinationStateId || edge.status, 18) }}</span>
            <small>{{ edge.observedResult }}</small>
            <button class="icon-btn" type="button" :aria-pressed="isImportant('transition', edge.id)" :disabled="reviewSaving" @click="toggleImportant('transition', edge.id)">{{ isImportant('transition', edge.id) ? 'Important flow' : 'Mark flow' }}</button>
          </li>
        </ul>
      </section>

      <section v-if="selectedState" class="discovery-detail evidence-browser">
        <div class="result-list-head evidence-head">
          <h4>State evidence</h4>
          <select v-model="selectedStateId" aria-label="Select discovered state">
            <option v-for="state in result.states" :key="state.id" :value="state.id">{{ shortLabel(state.title || state.url, 55) }}</option>
          </select>
        </div>
        <div class="evidence-grid">
          <img v-if="selectedState.screenshotUrl" :src="selectedState.screenshotUrl" :alt="`Screenshot of ${selectedState.title || selectedState.url}`" loading="lazy" />
          <div class="layout-outline">
            <p class="eyebrow">Structured layout</p>
            <h4>{{ selectedState.title || 'Untitled state' }}</h4>
            <a :href="selectedState.url" target="_blank" rel="noreferrer">{{ selectedState.url }}</a>
            <details v-if="selectedState.structure?.heading_outline?.length" open>
              <summary>Heading hierarchy ({{ selectedState.structure.heading_outline.length }})</summary>
              <ul><li v-for="(heading, index) in selectedState.structure.heading_outline" :key="`${index}-${heading.text}`"><strong>H{{ heading.level }}</strong> {{ heading.text }}</li></ul>
            </details>
            <details v-if="selectedState.structure?.landmarks?.length">
              <summary>Page landmarks ({{ selectedState.structure.landmarks.length }})</summary>
              <ul><li v-for="(landmark, index) in selectedState.structure.landmarks" :key="`${index}-${landmark.type}-${landmark.label}`"><strong>{{ landmark.type }}</strong><small>{{ landmark.label || 'Unlabelled region' }}</small></li></ul>
            </details>
            <details v-if="selectedState.structure?.sections?.length">
              <summary>Content regions ({{ selectedState.structure.sections.length }})</summary>
              <ul><li v-for="(section, index) in selectedState.structure.sections" :key="`${index}-${section.type}-${section.label}`"><strong>{{ section.type }}</strong><small>{{ section.label || 'Unlabelled region' }}</small></li></ul>
            </details>
            <details v-if="selectedState.structure?.navigation?.length">
              <summary>Navigation groups ({{ selectedState.structure.navigation.length }})</summary>
              <ul><li v-for="(group, index) in selectedState.structure.navigation" :key="`${index}-${group.label}`"><strong>{{ group.label || 'Navigation' }}</strong><small>{{ group.links.map((link) => link.text).filter(Boolean).join(' · ') || 'No named links' }}</small></li></ul>
            </details>
            <details v-if="selectedState.structure?.forms?.length">
              <summary>Forms ({{ selectedState.structure.forms.length }})</summary>
              <ul><li v-for="(form, index) in selectedState.structure.forms" :key="`${index}-${form.label}`"><strong>{{ form.label || 'Form' }}</strong><small>{{ form.fields.map((field) => field.name).filter(Boolean).join(' · ') || 'No visible fields' }}</small></li></ul>
            </details>
            <details><summary>Visible text</summary><p>{{ selectedState.visibleText || 'No visible text captured.' }}</p></details>
            <details><summary>Controls ({{ selectedActions.length }})</summary><ul><li v-for="action in selectedActions" :key="action.id"><strong>{{ action.control.name || action.control.role }}</strong><small>{{ action.safety }} · {{ action.status }} · {{ action.safetyReason }}</small></li></ul></details>
          </div>
        </div>
      </section>

      <section v-if="reviewActions.length" class="discovery-detail">
        <div class="result-list-head"><h4>Ambiguous action review</h4><span>{{ reviewActions.length }} actions</span></div>
        <p class="review-note">Approval records human intent for planning only. Review actions remain unexecuted by the safety policy.</p>
        <ul class="review-list">
          <li v-for="action in reviewActions" :key="action.id">
            <div><strong>{{ action.control.name || 'Unnamed control' }}</strong><small>{{ action.safetyReason }}</small></div>
            <div class="review-buttons">
              <button type="button" :class="{ active: runResult.review?.actions?.[action.id] === 'approved' }" :disabled="reviewSaving" @click="decideAction(action.id, 'approved')">Approve</button>
              <button type="button" :class="{ active: runResult.review?.actions?.[action.id] === 'rejected' }" :disabled="reviewSaving" @click="decideAction(action.id, 'rejected')">Reject</button>
            </div>
          </li>
        </ul>
      </section>

      <details v-if="result.events.length" class="manifest-preview">
        <summary>Run events and failures ({{ result.events.length }})</summary>
        <pre>{{ JSON.stringify(result.events, null, 2) }}</pre>
      </details>
    </div>
  </section>
</template>
