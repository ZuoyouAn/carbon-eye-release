import { createApp } from 'vue'
// Only the toast is shared with the home page; larger UI styles load with their views.
import 'element-plus/es/components/message/style/css'
import App from './App.vue'
import router from './router'
import './style.css'
import './design.css'
import { reveal } from './utils/reveal.js'

createApp(App).directive('reveal', reveal).use(router).mount('#app')
