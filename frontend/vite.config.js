import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { captureRunPlugin } from './server/capture-run-plugin.js'
import { discoveryRunPlugin } from './server/discovery-run-plugin.js'
import { renderJobRunPlugin } from './server/render-job-run-plugin.js'
import { contentPlanPlugin } from './server/content-plan-plugin.js'
import { localMediaPlugin } from './server/local-media-plugin.js'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), captureRunPlugin(), discoveryRunPlugin(), contentPlanPlugin(), renderJobRunPlugin(), localMediaPlugin()],
})
