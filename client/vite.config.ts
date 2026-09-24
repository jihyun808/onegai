import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: true,
    restoreMocks: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
  server: {
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
})
