<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import logoLight from './assets/mpostele-logo-light.png'
import logoDark from './assets/mpostele-logo-dark.png'
import DiscoveryPanel from './components/DiscoveryPanel.vue'
import PlanWorkspace from './components/PlanWorkspace.vue'
import RenderJobPanel from './components/RenderJobPanel.vue'
import { getSetting, setSetting } from './db/sqlite'

const theme = ref('light')
// Guards against persisting the defaults back to the database before the
// real stored values (if any) have finished loading.
const settingsLoaded = ref(false)
const activeNav = ref('overview')
const workspaceStatus = ref('Ready')
const discoveryHandoff = ref('')
const renderHandoff = ref(null)
const clipboardMessage = ref('')
const showPassword = ref(false)
const captureJob = ref({
  platformUrl: 'https://example.com',
  username: '',
  password: '',
  targetPath: '/dashboard',
  outputDir: 'artifacts/login_job',
})
const audioJob = ref({
  videoPath: 'artifacts/login_job/motion.mp4',
  audioPath: 'artifacts/login_job/voiceover.wav',
  outputPath: 'artifacts/login_job/final.mp4',
  normalizeAudio: true,
})

const pipelineSteps = [
  { title: 'Discover', text: 'Map pages, safe interface states, transitions, and evidence-backed product findings.', tone: 'citron' },
  { title: 'Login & route', text: 'Open a protected page with a supplied username and password.', tone: 'magenta' },
  { title: 'Capture', text: 'Take a clean screenshot of the target product state.', tone: 'lilac' },
  { title: 'Motion render', text: 'Apply the local FFmpeg-based Ken Burns style movement.', tone: 'tan' },
  { title: 'Narration', text: 'Match a local audio file to the visual and normalize its loudness.', tone: 'citron' },
  { title: 'Export', text: 'Write an H.264 and AAC clip into the artifacts folder.', tone: 'magenta' },
]

const isUrlValid = computed(() => {
  try {
    new URL(captureJob.value.platformUrl)
    return true
  } catch {
    return false
  }
})

const isOutputDirValid = computed(() => captureJob.value.outputDir.trim().length > 0)

const isJobValid = computed(() => isUrlValid.value && isOutputDirValid.value)
const isAudioJobValid = computed(() =>
  audioJob.value.videoPath.trim().length > 0 &&
  audioJob.value.audioPath.trim().length > 0 &&
  audioJob.value.outputPath.trim().length > 0
)

// 'idle' | 'running' | 'success' | 'error'
const runState = ref('idle')
const runResult = ref(null)
const isRunning = computed(() => runState.value === 'running')
const audioRunState = ref('idle')
const audioRunResult = ref(null)
const isAudioRunning = computed(() => audioRunState.value === 'running')

function quoteArgument(value) {
  return `"${value.replaceAll('"', '\\"')}"`
}

function buildCommandParts(mask) {
  const parts = [
    'python -m pipeline.first_render',
    `--url ${captureJob.value.platformUrl}`,
    `--base-dir ${captureJob.value.outputDir}`,
  ]

  if (captureJob.value.username) parts.push(`--username ${captureJob.value.username}`)
  if (captureJob.value.password) {
    parts.push(`--password ${mask ? '••••••••' : captureJob.value.password}`)
  }
  if (captureJob.value.targetPath) parts.push(`--target-path ${captureJob.value.targetPath}`)

  return parts.join(' ')
}

// Real command used for copying/running; may contain the plaintext password.
const jobCommand = computed(() => buildCommandParts(false))

// Masked command shown on screen so the password isn't exposed to shoulder-surfing or screenshots.
const displayCommand = computed(() => buildCommandParts(!showPassword.value))
const audioCommand = computed(() => {
  const parts = [
    'python -m pipeline.audio',
    `--video ${quoteArgument(audioJob.value.videoPath)}`,
    `--audio ${quoteArgument(audioJob.value.audioPath)}`,
    `--output ${quoteArgument(audioJob.value.outputPath)}`,
  ]
  if (!audioJob.value.normalizeAudio) parts.push('--no-normalize-audio')
  return parts.join(' ')
})

async function copyText(value, successMessage) {
  clipboardMessage.value = ''
  try {
    if (!navigator.clipboard) throw new Error('Clipboard access is unavailable')
    await navigator.clipboard.writeText(value)
    clipboardMessage.value = successMessage
  } catch (error) {
    clipboardMessage.value = error instanceof Error ? `Copy failed: ${error.message}` : 'Copy failed.'
  }
}

function copyCommand() {
  if (isJobValid.value) copyText(jobCommand.value, 'Capture command copied.')
}

// Triggers the actual local capture job by asking the Vite dev/preview
// server's /api/run-capture endpoint (see server/capture-run-plugin.js) to
// spawn `python -m pipeline.first_render` on this machine. The endpoint only
// accepts loopback requests and never puts the password on the command line.
function copyAudioCommand() {
  if (isAudioJobValid.value) copyText(audioCommand.value, 'Audio command copied.')
}

function useDiscoveryInPlan(snapshotPath) {
  discoveryHandoff.value = snapshotPath
  workspaceStatus.value = 'Discovery ready for planning'
  goToSection('plan')
}

function openDraftInRender(manifest) {
  renderHandoff.value = manifest
  workspaceStatus.value = 'Draft loaded in Render'
  goToSection('render')
}

function updateWorkspaceStatus(label, state) {
  workspaceStatus.value = `${label}: ${state}`
}

async function runCapture() {
  if (!isJobValid.value || isRunning.value) return

  runState.value = 'running'
  workspaceStatus.value = 'Capture: running'
  runResult.value = null

  try {
    const response = await fetch('/api/run-capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platformUrl: captureJob.value.platformUrl,
        username: captureJob.value.username,
        password: captureJob.value.password,
        targetPath: captureJob.value.targetPath,
        outputDir: captureJob.value.outputDir,
      }),
    })

    const data = await response.json()
    runResult.value = data
    runState.value = response.ok && data.code === 0 ? 'success' : 'error'
    workspaceStatus.value = `Capture: ${runState.value === 'success' ? 'completed' : 'failed'}`
  } catch (err) {
    runResult.value = { error: err instanceof Error ? err.message : String(err) }
    runState.value = 'error'
    workspaceStatus.value = 'Capture: failed'
  }
}

async function runAudio() {
  if (!isAudioJobValid.value || isAudioRunning.value) return

  audioRunState.value = 'running'
  workspaceStatus.value = 'Audio: compositing'
  audioRunResult.value = null

  try {
    const response = await fetch('/api/run-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(audioJob.value),
    })

    const data = await response.json()
    audioRunResult.value = data
    audioRunState.value = response.ok && data.code === 0 ? 'success' : 'error'
    workspaceStatus.value = `Audio: ${audioRunState.value === 'success' ? 'completed' : 'failed'}`
  } catch (err) {
    audioRunResult.value = { error: err instanceof Error ? err.message : String(err) }
    audioRunState.value = 'error'
    workspaceStatus.value = 'Audio: failed'
  }
}

// Use the light-background logo variant in light mode and the dark-background variant in dark mode.
const logoSrc = computed(() => (theme.value === 'light' ? logoLight : logoDark))

// The <link> favicons in index.html default to matching the OS color scheme
// via `prefers-color-scheme` media queries. Once the app's manual theme
// toggle is used, force the matching favicon regardless of OS preference by
// flipping each link's `media` between 'all' and 'not all'.
function syncFavicon(mode) {
  const lightIcon = document.getElementById('favicon-light')
  const darkIcon = document.getElementById('favicon-dark')
  if (lightIcon) lightIcon.media = mode === 'light' ? 'all' : 'not all'
  if (darkIcon) darkIcon.media = mode === 'dark' ? 'all' : 'not all'
}

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
  syncFavicon(theme.value)
}

function goToSection(id) {
  activeNav.value = id
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(async () => {
  const [storedTheme, storedJob, storedAudioJob] = await Promise.all([
    getSetting('theme'),
    getSetting('captureJob'),
    getSetting('audioJob'),
  ])

  if (storedTheme) theme.value = storedTheme
  if (storedJob) {
    // The password is intentionally never persisted, so it's simply absent
    // from the stored JSON and untouched here.
    Object.assign(captureJob.value, JSON.parse(storedJob))
  }
  if (storedAudioJob) Object.assign(audioJob.value, JSON.parse(storedAudioJob))

  document.documentElement.setAttribute('data-theme', theme.value)
  syncFavicon(theme.value)
  settingsLoaded.value = true
})

watch(theme, (value) => {
  if (!settingsLoaded.value) return
  setSetting('theme', value)
})

watch(
  captureJob,
  (job) => {
    if (!settingsLoaded.value) return
    const { password, ...persistable } = job
    setSetting('captureJob', JSON.stringify(persistable))
  },
  { deep: true }
)

watch(
  audioJob,
  (job) => {
    if (!settingsLoaded.value) return
    setSetting('audioJob', JSON.stringify(job))
  },
  { deep: true }
)
</script>

<template>
  <div class="site-shell">
    <header class="topbar">
      <div class="brand-wrap">
        <img class="brand-mark" :src="logoSrc" alt="Mpostele logo" />
        <div class="brand-copy">
          <div class="brand-name">Mpostele</div>
          <div class="brand-sub">Local capture studio</div>
        </div>
      </div>

      <nav class="main-nav" aria-label="Workspace navigation">
        <button v-for="item in [{ id: 'overview', label: 'Home' }, { id: 'discovery', label: 'Discover' }, { id: 'plan', label: 'Plan' }, { id: 'render', label: 'Render' }]" :key="item.id" class="nav-link" :class="{ 'is-active': activeNav === item.id }" :aria-current="activeNav === item.id ? 'page' : undefined" type="button" @click="goToSection(item.id)">{{ item.label }}</button>
        <span class="nav-divider" aria-hidden="true"></span>
        <button v-for="item in [{ id: 'capture', label: 'Capture' }, { id: 'audio', label: 'Audio' }, { id: 'docs', label: 'Guide' }]" :key="item.id" class="nav-link nav-tool" :class="{ 'is-active': activeNav === item.id }" :aria-current="activeNav === item.id ? 'page' : undefined" type="button" @click="goToSection(item.id)">{{ item.label }}</button>
      </nav>

      <button
        class="theme-switch"
        type="button"
        :aria-label="theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'"
        @click="toggleTheme"
      >
        {{ theme === 'light' ? '☾' : '☀' }}
      </button>
    </header>

    <div class="workspace-strip" aria-live="polite">
      <span class="status-dot"></span><strong>{{ workspaceStatus }}</strong>
      <span>Processed locally; capture connects to the target website.</span>
    </div>

    <main class="page">
      <section v-show="activeNav === 'overview'" id="overview" class="hero section-card">
        <div class="hero-copy">
          <p class="eyebrow">Local-first production studio</p>
          <h1>Your local video workspace.</h1>
          <p class="hero-text">Discover evidence, approve a focused story, and render lightweight product videos without a cloud pipeline.</p>
          <div class="hero-actions">
            <button class="primary-btn" type="button" @click="goToSection('discovery')">Start discovery</button>
            <button class="secondary-btn" type="button" @click="goToSection(discoveryHandoff ? 'plan' : 'capture')">{{ discoveryHandoff ? 'Continue planning' : 'Open capture tool' }}</button>
          </div>
        </div>
        <ol class="journey" aria-label="Primary workflow">
          <li><strong>1. Discover</strong><span>Collect safe, screenshot-backed product evidence.</span></li>
          <li><strong>2. Plan</strong><span>Review scenes and explicitly approve the story.</span></li>
          <li><strong>3. Render</strong><span>Build and preview a deterministic local export.</span></li>
        </ol>
      </section>

      <DiscoveryPanel v-show="activeNav === 'discovery'" @status="(state) => updateWorkspaceStatus('Discovery', state)" @use-in-plan="useDiscoveryInPlan" />

      <PlanWorkspace v-show="activeNav === 'plan'" :snapshot-path="discoveryHandoff" @status="(state) => updateWorkspaceStatus('Plan', state)" @open-render="openDraftInRender" />

      <section v-show="activeNav === 'capture'" id="capture" class="capture-panel section-card">
        <div class="section-head">
          <div>
            <p class="eyebrow">Capture setup</p>
            <h2>Platform login and target route</h2>
          </div>
        </div>

        <div class="form-grid">
          <label>
            Platform URL
            <input v-model="captureJob.platformUrl" type="url" placeholder="https://example.com" :aria-invalid="!isUrlValid" />
            <span v-if="!isUrlValid" class="field-error">Enter a valid URL, e.g. https://example.com</span>
          </label>

          <label>
            Username / email
            <input v-model="captureJob.username" type="text" placeholder="name@example.com" />
          </label>

          <label>
            Password
            <input v-model="captureJob.password" type="password" placeholder="••••••••" autocomplete="new-password" />
          </label>

          <label>
            Target path
            <input v-model="captureJob.targetPath" type="text" placeholder="/dashboard" />
          </label>

          <label>
            Output folder
            <input v-model="captureJob.outputDir" type="text" placeholder="artifacts/login_job" :aria-invalid="!isOutputDirValid" />
            <span v-if="!isOutputDirValid" class="field-error">Output folder cannot be empty</span>
          </label>
        </div>

        <details class="manifest-preview technical-details">
          <summary>Technical details and command</summary>
          <div class="command-box">
          <pre>{{ displayCommand }}</pre>
          <label v-if="captureJob.password" class="reveal-toggle">
            <input v-model="showPassword" type="checkbox" />
            Show password in command
          </label>
          <p v-if="captureJob.password" class="command-warning">The copied command includes your password in plain text. Only copy or paste it on a trusted machine.</p>
          </div>
          <button class="secondary-btn details-copy" type="button" :disabled="!isJobValid" @click="copyCommand">Copy command</button>
        </details>

        <div class="run-actions">
          <button class="primary-btn" type="button" :disabled="!isJobValid || isRunning" @click="runCapture">
            {{ isRunning ? 'Running…' : 'Run capture locally' }}
          </button>
          <p class="run-hint">Processed locally; capture connects to the target website.</p>
        </div>

        <div v-if="runResult" class="run-status" :class="runState">
          <p class="run-status-title">
            <template v-if="runState === 'success'">Capture finished successfully.</template>
            <template v-else-if="runResult.error">Failed to run: {{ runResult.error }}</template>
            <template v-else>Process exited with code {{ runResult.code }}.</template>
          </p>
          <pre v-if="runResult.stdout" class="run-log">{{ runResult.stdout }}</pre>
          <pre v-if="runResult.stderr" class="run-log run-log-error">{{ runResult.stderr }}</pre>
        </div>
      </section>

      <section v-show="activeNav === 'audio'" id="audio" class="capture-panel section-card">
        <div class="section-head">
          <div>
            <p class="eyebrow">Narration setup</p>
            <h2>Add a local voiceover to the motion clip</h2>
          </div>
        </div>

        <div class="form-grid">
          <label>
            Base video path
            <input v-model="audioJob.videoPath" type="text" placeholder="artifacts/login_job/motion.mp4" :aria-invalid="!audioJob.videoPath.trim()" />
            <span v-if="!audioJob.videoPath.trim()" class="field-error">Base video path cannot be empty</span>
          </label>

          <label>
            Narration audio path
            <input v-model="audioJob.audioPath" type="text" placeholder="artifacts/login_job/voiceover.wav" :aria-invalid="!audioJob.audioPath.trim()" />
            <span v-if="!audioJob.audioPath.trim()" class="field-error">Narration path cannot be empty</span>
          </label>

          <label>
            Final output path
            <input v-model="audioJob.outputPath" type="text" placeholder="artifacts/login_job/final.mp4" :aria-invalid="!audioJob.outputPath.trim()" />
            <span v-if="!audioJob.outputPath.trim()" class="field-error">Output path cannot be empty</span>
          </label>

          <label class="inline-checkbox">
            <input v-model="audioJob.normalizeAudio" type="checkbox" />
            Normalize narration loudness
          </label>
        </div>

        <details class="manifest-preview technical-details"><summary>Technical command</summary><div class="command-box"><pre>{{ audioCommand }}</pre></div></details>

        <div class="run-actions">
          <button class="primary-btn" type="button" :disabled="!isAudioJobValid || isAudioRunning" @click="runAudio">
            {{ isAudioRunning ? 'Compositing…' : 'Create narrated video' }}
          </button>
          <button class="secondary-btn" type="button" :disabled="!isAudioJobValid" @click="copyAudioCommand">Copy command</button>
          <p class="run-hint">All paths must stay inside this project. The files are processed locally with FFmpeg.</p>
        </div>

        <div v-if="audioRunResult" class="run-status" :class="audioRunState">
          <p class="run-status-title">
            <template v-if="audioRunState === 'success'">Narrated video created at {{ audioRunResult.outputPath }}.</template>
            <template v-else-if="audioRunResult.error">Failed to run: {{ audioRunResult.error }}</template>
            <template v-else>Process exited with code {{ audioRunResult.code }}.</template>
          </p>
          <pre v-if="audioRunResult.stdout" class="run-log">{{ audioRunResult.stdout }}</pre>
          <pre v-if="audioRunResult.stderr" class="run-log run-log-error">{{ audioRunResult.stderr }}</pre>
        </div>
      </section>

      <RenderJobPanel v-show="activeNav === 'render'" :imported-manifest="renderHandoff" @status="(state) => updateWorkspaceStatus('Render', state)" />

      <section v-show="activeNav === 'docs'" id="docs" class="steps-panel">
        <div class="section-head compact">
          <div>
            <p class="eyebrow">Implemented flow</p>
            <h2>What the project does today</h2>
          </div>
        </div>

        <div class="steps-grid">
          <article v-for="step in pipelineSteps" :key="step.title" class="step-card" :class="`tone-${step.tone}`">
            <span class="step-dot" :class="`step-dot--${step.tone}`"></span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.text }}</p>
          </article>
        </div>
      </section>
    </main>
    <p v-if="clipboardMessage" class="toast" role="status">{{ clipboardMessage }}</p>
  </div>
</template>
