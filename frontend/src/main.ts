import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { FrappeUIProvider } from 'frappe-ui'
import App from './App.vue'
import router from './router'
import './style.css'

// After a rebuild, a tab still running the previous bundle requests hashed
// chunks that no longer exist and the route renders blank. Reload once to
// pick up the new bundle; the timestamp guard stops a reload loop if the
// chunk is genuinely unavailable.
window.addEventListener('vite:preloadError', (event) => {
  const KEY = 'sirb:chunk-reload-at'
  try {
    if (Date.now() - Number(sessionStorage.getItem(KEY) || 0) < 10_000) return
    sessionStorage.setItem(KEY, String(Date.now()))
  } catch {
    // Storage blocked: without the guard a reload could loop, so don't.
    return
  }
  event.preventDefault()
  window.location.reload()
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.component('FrappeUIProvider', FrappeUIProvider)

app.mount('#app')
