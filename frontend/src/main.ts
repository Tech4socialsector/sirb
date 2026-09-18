import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { FrappeUIProvider } from 'frappe-ui'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.component('FrappeUIProvider', FrappeUIProvider)

app.mount('#app')
