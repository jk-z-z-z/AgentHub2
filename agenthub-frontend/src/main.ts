import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { applyThemeToDocument, getStoredTheme } from './stores/theme'
import './styles/tokens.css'
import './styles/theme.css'

applyThemeToDocument(getStoredTheme())

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
