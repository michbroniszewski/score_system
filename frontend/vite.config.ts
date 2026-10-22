import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  server: {
    // In development the site reads the live API. API_PROXY_TARGET is set in compose.yaml
    // (the api service); when running `npm run dev` on the host it is the local port.
    // xfwd adds X-Forwarded-Host, which the API compares with Origin to accept changes
    // from this site (see same_origin_writes in backend/src/score_system/api/main.py).
    proxy: {
      '/api': { target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000', xfwd: true },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
