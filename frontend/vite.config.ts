import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  server: {
    // In development the site reads the live API. API_PROXY_TARGET is set in compose.yaml
    // (the api service); when running `npm run dev` on the host it is the local port.
    proxy: { '/api': process.env.API_PROXY_TARGET ?? 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
  },
})
