import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:7777',
    },
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,vue}'],
      exclude: ['src/main.js', 'src/router/index.js'],
      reporter: ['text', 'lcov', 'cobertura'],
      reportsDirectory: '../reports/frontend-coverage',
      thresholds: { lines: 90, branches: 75 },
    },
  },
})
