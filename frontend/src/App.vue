<script setup>
import { onMounted, ref } from 'vue'

const theme = ref('light')

const navItems = ['Overview', 'Calendar', 'Composer', 'Insights']
const channels = [
  { name: 'All', tone: 'magenta', active: true },
  { name: 'Instagram', tone: 'lilac' },
  { name: 'LinkedIn', tone: 'tan' },
  { name: 'X', tone: 'rose' },
  { name: 'Facebook', tone: 'wheat' },
  { name: 'YouTube', tone: 'citron' },
]

const metrics = [
  { label: 'Reach', value: '137k', badge: '+42%', tone: 'magenta' },
  { label: 'Engagement', value: '8.4%', badge: '+1.2%', tone: 'lilac' },
  { label: 'Best slot', value: '08:30', badge: 'Instagram', tone: 'wheat' },
  { label: 'Spend', value: 'P790', badge: 'Budget', tone: 'gray' },
]

const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const calendarSlots = [
  { label: 'Launch', time: '08:30', tone: 'magenta' },
  { label: 'Story', time: '10:15', tone: 'lilac' },
  { label: 'Trend', time: '13:00', tone: 'rose' },
  { label: 'Case', time: '16:40', tone: 'tan' },
  { label: 'Photo', time: '09:10', tone: 'tan' },
  { label: 'Event', time: '11:45', tone: 'wheat' },
  { label: 'Video', time: '18:05', tone: 'citron' },
  { label: 'UGC', time: '07:55', tone: 'magenta' },
  { label: 'Carousel', time: '09:35', tone: 'lilac' },
  { label: 'Reply', time: '12:20', tone: 'rose' },
  { label: 'Feature', time: '14:15', tone: 'wheat' },
  { label: 'Promo', time: '19:00', tone: 'citron' },
]

const draftQueue = [
  { campaign: 'Product launch story', channel: 'Instagram', tone: 'lilac', due: '08:30', status: 'Queued', statusTone: 'magenta', reach: '42k' },
  { campaign: 'Customer win recap', channel: 'LinkedIn', tone: 'tan', due: '09:20', status: 'Draft', statusTone: 'gray', reach: '18k' },
  { campaign: 'Founder note', channel: 'X', tone: 'rose', due: '12:15', status: 'Review', statusTone: 'wheat', reach: '7k' },
  { campaign: 'Monthly roundup', channel: 'Facebook', tone: 'wheat', due: '14:45', status: 'Ready', statusTone: 'citron', reach: '31k' },
]

const bestTimes = [
  { label: 'Instagram', value: '08:30' },
  { label: 'LinkedIn', value: '09:20' },
  { label: 'X', value: '12:15' },
  { label: 'Facebook', value: '14:45' },
  { label: 'YouTube', value: '18:05' },
]

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
}

onMounted(() => {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light'
  theme.value = currentTheme
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand-wrap">
        <div class="brand-mark">M</div>
        <div class="brand-copy">
          <div class="brand-name">Mpostele</div>
          <div class="brand-sub">Planner</div>
        </div>
      </div>

      <nav class="top-nav" aria-label="Primary navigation">
        <button
          v-for="(item, index) in navItems"
          :key="item"
          class="nav-action"
          :class="{ 'is-selected': index === 0 }"
          type="button"
        >
          {{ item }}
        </button>
      </nav>

      <div class="header-actions">
        <button class="icon-button" aria-label="Toggle theme" type="button" @click="toggleTheme">
          {{ theme === 'light' ? '☼' : '☾' }}
        </button>
        <button class="mp-btn mp-btn--primary" type="button">Schedule</button>
      </div>
    </header>

    <aside class="side-rail" aria-label="Channel rail">
      <div class="rail-title">Channels</div>

      <div
        v-for="channel in channels"
        :key="channel.name"
        class="rail-item"
        :class="{ 'is-active': channel.active }"
      >
        <span class="rail-dot" :class="`rail-dot--${channel.tone}`"></span>
        <span>{{ channel.name }}</span>
      </div>
    </aside>

    <main class="workspace">
      <section class="page-header">
        <div>
          <p class="mp-label-01 page-overline">WEEK 37 · 8–14 SEPTEMBER</p>
          <h1 class="mp-heading-04">24 posts scheduled across five channels</h1>
        </div>

        <div class="page-actions">
          <button class="mp-btn mp-btn--secondary" type="button">Approve all</button>
          <button class="mp-btn mp-btn--primary" type="button">Schedule</button>
        </div>
      </section>

      <section class="kpi-grid" aria-label="Key metrics">
        <article v-for="metric in metrics" :key="metric.label" class="metric-card">
          <p class="mp-label-01">{{ metric.label }}</p>
          <div class="metric-row">
            <h2 class="mp-heading-05">{{ metric.value }}</h2>
            <span class="mp-tag" :class="`mp-tag--${metric.tone}`">{{ metric.badge }}</span>
          </div>
        </article>
      </section>

      <section class="content-grid">
        <article class="panel panel--wide">
          <div class="panel-header">
            <h2 class="mp-heading-03">Content calendar</h2>
            <div class="segmented-control" aria-label="View options">
              <button class="segmented is-selected" type="button">Month</button>
              <button class="segmented" type="button">Week</button>
              <button class="segmented" type="button">List</button>
            </div>
          </div>

          <div class="calendar-grid" aria-label="Calendar preview">
            <div v-for="day in weekDays" :key="day" class="calendar-day muted">{{ day }}</div>

            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--magenta"><span>Launch</span><small>08:30</small></div>
            <div class="slot slot--lilac"><span>Story</span><small>10:15</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--rose"><span>Trend</span><small>13:00</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--tan"><span>Case</span><small>16:40</small></div>

            <div class="slot slot--tan"><span>Photo</span><small>09:10</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--wheat"><span>Event</span><small>11:45</small></div>
            <div class="slot slot--citron"><span>Video</span><small>18:05</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--magenta"><span>UGC</span><small>07:55</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>

            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--lilac"><span>Carousel</span><small>09:35</small></div>
            <div class="slot slot--rose"><span>Reply</span><small>12:20</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--wheat"><span>Feature</span><small>14:15</small></div>
            <div class="slot slot--empty" aria-hidden="true"></div>
            <div class="slot slot--citron"><span>Promo</span><small>19:00</small></div>
          </div>
        </article>

        <article class="panel">
          <div class="panel-header">
            <h2 class="mp-heading-03">Best times</h2>
            <button class="text-link" type="button">View all</button>
          </div>

          <ul class="channel-list">
            <li v-for="time in bestTimes" :key="time.label">
              <span>{{ time.label }}</span>
              <strong>{{ time.value }}</strong>
            </li>
          </ul>
        </article>
      </section>

      <section class="panel table-panel">
        <div class="panel-header">
          <h2 class="mp-heading-03">Draft queue</h2>
          <button class="mp-btn mp-btn--secondary" type="button">Review</button>
        </div>

        <table class="mp-table">
          <thead>
            <tr>
              <th>Campaign</th>
              <th>Channel</th>
              <th>Due</th>
              <th>Status</th>
              <th>Reach</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="item in draftQueue" :key="item.campaign">
              <td>{{ item.campaign }}</td>
              <td><span class="mp-tag" :class="`mp-tag--${item.tone}`">{{ item.channel }}</span></td>
              <td>{{ item.due }}</td>
              <td><span class="mp-tag" :class="`mp-tag--${item.statusTone}`">{{ item.status }}</span></td>
              <td>{{ item.reach }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>
