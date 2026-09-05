<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import logoLight from './assets/mpostele-logo-light.png'
import logoDark from './assets/mpostele-logo-dark.png'
import { getSetting, setSetting } from './db/sqlite'

const theme = ref('light')
// Guards against persisting the defaults back to the database before the
// real stored values (if any) have finished loading.
const settingsLoaded = ref(false)
const activeNav = ref('overview')
const showPassword = ref(false)
const captureJob = ref({
  platformUrl: 'https://example.com',
  username: '',
  password: '',
  targetPath: '/dashboard',
  outputDir: 'artifacts/login_job',
})

const pipelineSteps = [
  { title: 'Login & route', text: 'Open a protected page with a supplied username and password.', tone: 'magenta' },
  { title: 'Capture', text: 'Take a clean screenshot of the target product state.', tone: 'lilac' },
  { title: 'Motion render', text: 'Apply the local FFmpeg-based Ken Burns style movement.', tone: 'tan' },
  { title: 'Export', text: 'Write a final social-ready clip into the artifacts folder.', tone: 'citron' },
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

// 'idle' | 'running' | 'success' | 'error'
const runState = ref('idle')
const runResult = ref(null)
const isRunning = computed(() => runState.value === 'running')

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

function copyCommand() {
  if (!isJobValid.value) return
  navigator.clipboard?.writeText(jobCommand.value)
}

// Triggers the actual local capture job by asking the Vite dev/preview
// server's /api/run-capture endpoint (see server/capture-run-plugin.js) to
// spawn `python -m pipeline.first_render` on this machine. The endpoint only
// accepts loopback requests and never puts the password on the command line.
async function runCapture() {
  if (!isJobValid.value || isRunning.value) return

  runState.value = 'running'
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
  } catch (err) {
    runResult.value = { error: err instanceof Error ? err.message : String(err) }
    runState.value = 'error'
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
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(async () => {
  const [storedTheme, storedJob] = await Promise.all([
    getSetting('theme'),
    getSetting('captureJob'),
  ])

  if (storedTheme) theme.value = storedTheme
  if (storedJob) {
    // The password is intentionally never persisted, so it's simply absent
    // from the stored JSON and untouched here.
    Object.assign(captureJob.value, JSON.parse(storedJob))
  }

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

      <nav class="main-nav" aria-label="Main navigation">
        <button
          class="nav-link"
          :class="{ 'is-active': activeNav === 'overview' }"
          :aria-current="activeNav === 'overview' ? 'page' : undefined"
          type="button"
          @click="goToSection('overview')"
        >Overview</button>
        <button
          class="nav-link"
          :class="{ 'is-active': activeNav === 'capture' }"
          :aria-current="activeNav === 'capture' ? 'page' : undefined"
          type="button"
          @click="goToSection('capture')"
        >Capture</button>
        <button
          class="nav-link"
          :class="{ 'is-active': activeNav === 'docs' }"
          :aria-current="activeNav === 'docs' ? 'page' : undefined"
          type="button"
          @click="goToSection('docs')"
        >Docs</button>
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

    <main class="page">
      <section id="overview" class="hero section-card">
        <div class="hero-copy">
          <p class="eyebrow">Local-first workflow</p>
          <h1>Capture product pages and turn them into motion-ready clips.</h1>
          <p class="hero-text">
            This pipeline logs in, navigates to a target page, captures the state, and renders a lightweight local motion video without relying on a heavy cloud stack.
          </p>
          <div class="hero-actions">
            <button class="primary-btn" type="button" @click="goToSection('capture')">Get started</button>
            <button class="secondary-btn" type="button" :disabled="!isJobValid" @click="copyCommand">Copy command</button>
          </div>
        </div>

        <div class="hero-visual" aria-hidden="true">
          <div class="mock-window">
            <div class="mock-toolbar">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div class="mock-body">
              <aside class="mock-sidebar"></aside>
              <div class="mock-content">
                <div class="mock-row long"></div>
                <div class="mock-grid">
                  <div class="mock-card"></div>
                  <div class="mock-card"></div>
                  <div class="mock-card large"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="capture" class="capture-panel section-card">
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

        <div class="command-box">
          <pre>{{ displayCommand }}</pre>
          <label v-if="captureJob.password" class="reveal-toggle">
            <input v-model="showPassword" type="checkbox" />
            Show password in command
          </label>
          <p v-if="captureJob.password" class="command-warning">
            The copied command includes your password in plain text. Only copy or paste it on a trusted machine.
          </p>
        </div>

        <div class="run-actions">
          <button class="primary-btn" type="button" :disabled="!isJobValid || isRunning" @click="runCapture">
            {{ isRunning ? 'Running…' : 'Run capture locally' }}
          </button>
          <p class="run-hint">Runs the command above directly on this machine via the local dev server. Nothing leaves your computer.</p>
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

      <section id="docs" class="steps-panel">
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
  </div>
</template>
