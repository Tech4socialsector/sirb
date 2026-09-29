import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    frappeui({
      frontendRoute: '/sirb',
      jinjaBootData: true,
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // Vite 8 (rolldown-vite) defaults CSS minification to lightningcss,
    // which was observed silently dropping some compiled Tailwind utility
    // rules (e.g. bare `.text-ink`, `.bg-surface`, any `bg-slate-900*`
    // rule disappeared from the built CSS entirely — not a purge/
    // content-scan issue, the rules just never survived minification).
    // esbuild would be the usual alternative but this build doesn't ship
    // it as a dependency; disabling minification is the safe fix — CSS
    // stays correct, at the cost of a larger (unminified) stylesheet.
    cssMinify: false,
  },
})
