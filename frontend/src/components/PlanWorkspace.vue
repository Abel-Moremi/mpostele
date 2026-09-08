<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getSetting, setSetting } from '../db/sqlite'

const props = defineProps({ snapshotPath: { type: String, default: '' } })
const emit = defineEmits(['status', 'open-render'])

function keyFor(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
const days = Array.from({ length: 7 }, (_, offset) => {
  const date = new Date(); date.setHours(0, 0, 0, 0); date.setDate(date.getDate() + offset)
  return { key: keyFor(date), weekday: new Intl.DateTimeFormat(undefined, { weekday: 'short' }).format(date), label: new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date) }
})
const settingsLoaded = ref(false)
const config = ref({
  scheduledDate: days[0].key,
  snapshotPath: 'artifacts/site-analysis/run/snapshot.json', reviewPath: '',
  outputPath: `artifacts/content-plans/${days[0].key}-week.json`,
  planningPrompt: 'Introduce the product, lead with the clearest customer benefit, demonstrate the supporting workflow, and end with a practical next step.',
  objective: 'product overview', audience: 'prospective users',
  platform: 'shorts', duration: 30, tone: 'clear and practical', callToAction: 'Learn more', maxScenes: 6,
  wordsPerMinute: 145, provider: 'heuristic', endpoint: 'http://127.0.0.1:8080/v1/chat/completions', model: 'qwen3-4b-instruct',
})
const plan = ref(null)
const planPath = ref('')
const manifestPath = ref(`artifacts/render-jobs/${days[0].key}-draft.json`)
const runState = ref('idle')
const message = ref('')
const result = ref(null)
const hasUnsavedChanges = ref(false)
const selectedPostDate = ref(days[0].key)

const approvedCount = computed(() => plan.value?.scenes.filter((scene) => scene.review_status === 'approved').length || 0)
const rejectedCount = computed(() => plan.value?.scenes.filter((scene) => scene.review_status === 'rejected').length || 0)
const pendingCount = computed(() => plan.value?.scenes.filter((scene) => scene.review_status === 'pending').length || 0)
const plannedDuration = computed(() => plan.value?.scenes.filter((scene) => scene.review_status !== 'rejected').reduce((total, scene) => total + Number(scene.estimated_duration_seconds || 0), 0) || 0)
const narrationWords = computed(() => plan.value?.scenes.filter((scene) => scene.review_status !== 'rejected').reduce((total, scene) => total + scene.narration.trim().split(/\s+/).filter(Boolean).length, 0) || 0)
const promptLength = computed(() => config.value.planningPrompt?.length || 0)
const selectedPost = computed(() => plan.value?.weekly_posts?.find((post) => post.scheduled_for === selectedPostDate.value) || plan.value?.weekly_posts?.[0] || null)
const canConvert = computed(() => plan.value?.status === 'approved' && selectedPost.value?.review_status === 'approved' && selectedPost.value.scene_ids.some((id) => plan.value.scenes.some((scene) => scene.id === id && scene.review_status === 'approved')))
const configValid = computed(() => config.value.snapshotPath.trim() && config.value.outputPath.trim() && config.value.planningPrompt?.trim() && promptLength.value <= 2000 && config.value.objective.trim() && config.value.audience.trim() && config.value.tone.trim())

const promptExamples = [
  'Lead with the weekly calendar, show how a small team plans a campaign, and end with the publishing benefit.',
  'Create a fast feature launch teaser for new users. Prioritize the clearest before-and-after workflow.',
  'Explain the product in a calm educational sequence for prospective customers who are seeing it for the first time.',
]

function sceneScreenshotPath(scene) {
  const screenshot = scene.evidence.screenshot_path.replaceAll('\\', '/')
  if (/^(?:[A-Za-z]:\/|\/)/.test(screenshot)) return screenshot
  const snapshot = (plan.value?.source?.snapshot || config.value.snapshotPath).replaceAll('\\', '/')
  return `${snapshot.slice(0, snapshot.lastIndexOf('/') + 1)}${screenshot}`
}

function selectDate(value) {
  const old = config.value.scheduledDate
  const previousDefault = `artifacts/content-plans/${old}-week.json`
  config.value.scheduledDate = value
  if (config.value.outputPath === previousDefault) config.value.outputPath = `artifacts/content-plans/${value}-week.json`
}
function selectPost(post) {
  selectedPostDate.value = post.scheduled_for
  manifestPath.value = `artifacts/render-jobs/${post.scheduled_for}-draft.json`
}
function postChanged(post) {
  post.review_status = 'pending'
  plan.value.status = 'pending_review'
  hasUnsavedChanges.value = true
}
function setPostStatus(post, status) {
  selectPost(post)
  post.review_status = status
  plan.value.status = 'pending_review'
  hasUnsavedChanges.value = true
}
function sceneChanged(scene) {
  scene.review_status = 'pending'
  plan.value.weekly_posts.filter((post) => post.scene_ids.includes(scene.id)).forEach((post) => { post.review_status = 'pending' })
  plan.value.status = 'pending_review'
  hasUnsavedChanges.value = true
}
function setSceneStatus(scene, status) {
  scene.review_status = status
  plan.value.status = 'pending_review'
  hasUnsavedChanges.value = true
}
function moveScene(index, offset) {
  const target = index + offset
  if (target < 0 || target >= plan.value.scenes.length) return
  const [scene] = plan.value.scenes.splice(index, 1)
  plan.value.scenes.splice(target, 0, scene)
  plan.value.status = 'pending_review'
  hasUnsavedChanges.value = true
}
function approvePlan() {
  plan.value.scenes.forEach((scene) => { if (scene.review_status !== 'rejected') scene.review_status = 'approved' })
  plan.value.weekly_posts.forEach((post) => { if (post.review_status !== 'rejected') post.review_status = 'approved' })
  plan.value.status = 'approved'
  hasUnsavedChanges.value = true
}

async function request(payload) {
  runState.value = 'running'; message.value = ''; result.value = null; emit('status', 'working')
  try {
    const response = await fetch('/api/content-plans', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    const data = await response.json()
    if (!response.ok || data.code) throw new Error(data.error || data.stderr || `Request failed (${response.status})`)
    runState.value = 'success'; result.value = data; emit('status', 'ready')
    return data
  } catch (error) {
    runState.value = 'error'; message.value = error instanceof Error ? error.message : String(error); emit('status', 'failed')
    return null
  }
}
async function generatePlan() {
  if (!configValid.value) return
  const data = await request({ action: 'generate', job: config.value })
  if (data) { plan.value = data.plan; planPath.value = data.planPath; selectedPostDate.value = data.plan.weekly_posts[0].scheduled_for; hasUnsavedChanges.value = false; message.value = 'Seven daily content directions generated and ready for review.' }
}
async function loadPlan() {
  const target = planPath.value.trim() || config.value.outputPath.trim()
  if (!target) return
  const data = await request({ action: 'load', planPath: target })
  if (data) {
    plan.value = data.plan; planPath.value = data.planPath; hasUnsavedChanges.value = false
    const campaignStart = data.plan.campaign?.start_date || data.plan.scheduled_for
    if (days.some((day) => day.key === campaignStart)) config.value.scheduledDate = campaignStart
    selectedPostDate.value = data.plan.weekly_posts?.[0]?.scheduled_for || campaignStart
    message.value = 'Plan loaded.'
  }
}
async function savePlan() {
  if (!plan.value) return
  plan.value.scheduled_for = config.value.scheduledDate
  const target = planPath.value.trim() || config.value.outputPath.trim()
  const data = await request({ action: 'save', planPath: target, plan: plan.value })
  if (data) { planPath.value = data.planPath; hasUnsavedChanges.value = false; message.value = 'Plan edits saved locally.' }
}
async function convertPlan() {
  if (!canConvert.value) return
  await savePlan()
  if (runState.value === 'error') return
  const data = await request({ action: 'convert', planPath: planPath.value, manifestPath: manifestPath.value, options: { scheduledDate: selectedPostDate.value } })
  if (data) {
    message.value = `Draft render manifest saved to ${data.manifestPath}. Inspect it before running the render job.`
    emit('open-render', data.manifest)
  }
}

onMounted(async () => {
  const stored = await getSetting('planWorkspace')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      Object.assign(config.value, parsed.config || {})
      planPath.value = parsed.planPath || ''
      manifestPath.value = parsed.manifestPath || manifestPath.value
      if (!days.some((day) => day.key === config.value.scheduledDate)) config.value.scheduledDate = days[0].key
    } catch { /* Ignore malformed older local settings. */ }
  }
  settingsLoaded.value = true
})
watch(() => props.snapshotPath, (value) => {
  if (value) config.value.snapshotPath = value
}, { immediate: true })
watch([config, planPath, manifestPath], () => {
  if (settingsLoaded.value) setSetting('planWorkspace', JSON.stringify({ config: config.value, planPath: planPath.value, manifestPath: manifestPath.value }))
}, { deep: true })
</script>

<template>
  <section id="plan" class="capture-panel section-card">
    <div class="section-head discovery-heading">
      <div>
        <p class="eyebrow">Evidence-backed planning</p>
        <h2>Turn one prompt into a week of content</h2>
        <p class="section-description">Describe the campaign once. The local agent develops a distinct post direction for each of the next seven days, grounded in discovery evidence.</p>
      </div>
      <span class="local-badge">Local files only</span>
    </div>

    <div class="planning-step"><span>1</span><div><strong>Describe the campaign</strong><small>Start with the outcome you want. The agent will turn it into seven connected daily directions.</small></div></div>
    <div class="prompt-card">
      <label for="planning-prompt">What should this week of content achieve?</label>
      <textarea id="planning-prompt" v-model="config.planningPrompt" rows="5" maxlength="2000" :aria-invalid="!config.planningPrompt.trim() || promptLength > 2000" placeholder="Describe the story, feature, audience need, sequence, and desired takeaway."></textarea>
      <div class="prompt-meta"><span>Be specific about what to prioritize, not facts to invent.</span><span>{{ promptLength }} / 2000</span></div>
      <div class="prompt-examples" aria-label="Prompt examples">
        <button v-for="(example, index) in promptExamples" :key="example" type="button" @click="config.planningPrompt = example">Use example {{ index + 1 }}</button>
      </div>
      <span v-if="!config.planningPrompt.trim()" class="field-error">Add a planning prompt before generating.</span>
    </div>

    <div class="planning-step"><span>2</span><div><strong>Set the campaign boundaries</strong><small>Choose when the seven-day sequence starts and which evidence, audience, and channel it should use.</small></div></div>
    <div class="week-strip" aria-label="Campaign start date">
      <button v-for="day in days" :key="day.key" type="button" :class="{ active: config.scheduledDate === day.key }" @click="selectDate(day.key)">
        <span>{{ day.weekday }}</span><strong>{{ day.label }}</strong><small>{{ day.key === days[0].key ? 'Start today' : 'Start here' }}</small>
      </button>
    </div>
    <div class="form-grid plan-config">
      <label class="wide-field">Discovery evidence<input v-model="config.snapshotPath" type="text" /><span class="field-help">Path to the snapshot created in Discover.</span></label>
      <label>Goal<input v-model="config.objective" type="text" /></label>
      <label>Audience<input v-model="config.audience" type="text" /></label>
      <label>Channel<select v-model="config.platform"><option value="shorts">YouTube Shorts</option><option value="reels">Instagram Reels</option><option value="tiktok">TikTok</option><option value="landscape">Landscape video</option><option value="square">Square video</option></select></label>
      <label>Target length (seconds)<input v-model.number="config.duration" type="number" min="5" max="300" /></label>
    </div>
    <details class="advanced-settings">
      <summary>Advanced planning settings <span>{{ config.maxScenes }} scenes · {{ config.provider }}</span></summary>
      <div class="form-grid plan-config">
        <label>Review path (optional)<input v-model="config.reviewPath" type="text" /></label>
        <label>Content-plan output path<input v-model="config.outputPath" type="text" /></label>
        <label>Maximum scenes<input v-model.number="config.maxScenes" type="number" min="1" max="20" /></label>
        <label>Tone<input v-model="config.tone" type="text" /></label>
        <label>Call to action<input v-model="config.callToAction" type="text" /></label>
        <label>Planning provider<select v-model="config.provider"><option value="heuristic">Deterministic heuristic</option><option value="llama.cpp">Local llama.cpp</option></select></label>
        <label v-if="config.provider === 'llama.cpp'">Local endpoint<input v-model="config.endpoint" type="url" /></label>
      </div>
    </details>

    <div class="planning-step"><span>3</span><div><strong>Develop the week</strong><small>The agent creates seven daily post directions plus reusable evidence-backed production scenes. Nothing is published.</small></div></div>
    <div class="run-actions plan-generate-actions">
      <button class="primary-btn" type="button" :disabled="!configValid || runState === 'running'" @click="generatePlan">{{ runState === 'running' ? 'Developing the week…' : 'Develop seven-day plan' }}</button>
      <p class="run-hint">{{ configValid ? `Uses ${config.provider === 'heuristic' ? 'deterministic local planning' : 'your local llama.cpp server'}.` : 'Complete the prompt and required fields to continue.' }}</p>
    </div>
    <details class="advanced-settings load-plan">
      <summary>Open an existing plan <span>{{ planPath || 'Choose a local JSON file path' }}</span></summary>
      <div class="load-plan-controls">
        <label class="plan-load-field">Existing plan path<input v-model="planPath" type="text" placeholder="artifacts/content-plans/2026-01-01.json" /></label>
        <button class="secondary-btn" type="button" :disabled="runState === 'running' || !(planPath || config.outputPath)" @click="loadPlan">Load plan</button>
      </div>
    </details>

    <div v-if="message" class="run-status" :class="runState"><p class="run-status-title">{{ message }}</p></div>

    <div v-if="plan" class="plan-review">
      <div class="plan-summary">
        <div><p class="eyebrow">Review queue</p><h3>{{ plan.brief.objective }}</h3><p>{{ plan.brief.audience }} · {{ plan.brief.platform }} · target {{ plan.brief.target_duration_seconds }} seconds</p><p v-if="plan.brief.planning_prompt" class="plan-prompt-summary">“{{ plan.brief.planning_prompt }}”</p><span class="save-state" :class="{ dirty: hasUnsavedChanges }">{{ hasUnsavedChanges ? 'Unsaved changes' : 'Saved locally' }}</span></div>
        <div class="plan-counts"><span>7 daily posts</span><span>{{ plan.scenes.length }} evidence scenes</span><span>{{ plannedDuration.toFixed(1) }} sec</span><span>{{ narrationWords }} words</span><span>{{ approvedCount }} scenes approved</span><span v-if="pendingCount">{{ pendingCount }} pending</span><span v-if="rejectedCount">{{ rejectedCount }} rejected</span></div>
      </div>

      <div class="weekly-direction-grid" aria-label="Generated daily content directions">
        <article v-for="post in plan.weekly_posts" :key="post.id" class="daily-direction" :class="[{ selected: selectedPostDate === post.scheduled_for }, `review-${post.review_status}`]" @click="selectPost(post)">
          <div class="daily-direction-head"><div><span>{{ new Date(`${post.scheduled_for}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short' }) }}</span><strong>{{ new Date(`${post.scheduled_for}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }}</strong></div><span class="review-pill">{{ post.review_status }}</span></div>
          <label>Daily theme<input v-model="post.theme" type="text" @click.stop @input="postChanged(post)" /></label>
          <label>Content direction<textarea v-model="post.content_direction" rows="3" @click.stop @input="postChanged(post)"></textarea></label>
          <label>Hook<input v-model="post.hook" type="text" @click.stop @input="postChanged(post)" /></label>
          <div class="daily-meta"><span>{{ post.format }}</span><span>{{ post.scene_ids.length }} evidence scene{{ post.scene_ids.length === 1 ? '' : 's' }}</span></div>
          <div class="review-buttons" @click.stop><button type="button" :class="{ active: post.review_status === 'approved' }" @click="setPostStatus(post, 'approved')">Approve day</button><button type="button" :class="{ rejected: post.review_status === 'rejected' }" @click="setPostStatus(post, 'rejected')">Reject day</button></div>
        </article>
      </div>

      <div class="planning-step"><span>4</span><div><strong>Review production scenes</strong><small>These screenshot-backed scenes support the daily directions above and can be reused across the week.</small></div></div>
      <article v-for="(scene, index) in plan.scenes" :key="scene.id" class="plan-scene" :class="`review-${scene.review_status}`">
        <div class="scene-toolbar">
          <div><span class="scene-number">{{ index + 1 }}</span><strong>{{ scene.id }}</strong><span class="review-pill">{{ scene.review_status }}</span></div>
          <div class="scene-actions"><button type="button" :disabled="index === 0" @click="moveScene(index, -1)">Up</button><button type="button" :disabled="index === plan.scenes.length - 1" @click="moveScene(index, 1)">Down</button></div>
        </div>
        <div class="plan-scene-body">
          <img class="scene-thumbnail" :src="`/api/local-media?file=${encodeURIComponent(sceneScreenshotPath(scene))}`" :alt="`Evidence for ${scene.id}`" loading="lazy" />
        <div class="form-grid scene-grid">
          <label>Purpose<input v-model="scene.purpose" type="text" @input="sceneChanged(scene)" /></label>
          <label>Estimated seconds<input v-model.number="scene.estimated_duration_seconds" type="number" min="0.1" step="0.1" @input="sceneChanged(scene)" /></label>
          <label class="wide-field">Narration<textarea v-model="scene.narration" rows="3" @input="sceneChanged(scene)"></textarea></label>
          <label class="wide-field">Overlay text<input v-model="scene.overlay.text" type="text" @input="sceneChanged(scene)" /></label>
        </div>
        </div>
        <div class="evidence-line"><span>State <strong>{{ scene.evidence.state_id }}</strong></span><span>Screenshot <code>{{ scene.evidence.screenshot_path }}</code></span><span>Confidence {{ Math.round(scene.confidence * 100) }}%</span></div>
        <div class="review-buttons"><button type="button" :class="{ active: scene.review_status === 'approved' }" @click="setSceneStatus(scene, 'approved')">Approve scene</button><button type="button" :class="{ rejected: scene.review_status === 'rejected' }" @click="setSceneStatus(scene, 'rejected')">Reject scene</button></div>
      </article>

      <div class="plan-footer">
        <div class="run-actions"><button class="secondary-btn" type="button" :disabled="runState === 'running' || !hasUnsavedChanges" @click="savePlan">Save edits</button><button class="primary-btn" type="button" :disabled="runState === 'running' || plan.status === 'approved'" @click="approvePlan">Approve plan</button></div>
        <div class="draft-manifest"><label>Draft manifest for {{ selectedPost?.scheduled_for }}<input v-model="manifestPath" type="text" /></label><button class="primary-btn" type="button" :disabled="!canConvert || runState === 'running'" @click="convertPlan">Open selected day in Render</button></div>
      </div>
      <details v-if="result?.manifest" class="manifest-preview"><summary>Preview draft manifest</summary><pre>{{ JSON.stringify(result.manifest, null, 2) }}</pre></details>
    </div>
  </section>
</template>
