import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { captureRunPlugin } from './server/capture-run-plugin.js'
import { renderJobRunPlugin } from './server/render-job-run-plugin.js'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), captureRunPlugin(), renderJobRunPlugin()],
})
