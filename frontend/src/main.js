import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import VueAxios from 'vue-axios'
// 导入vuetify组件库
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'

const app = createApp(App)

const vuetify = createVuetify({
  components,
  directives,
})

// 注册插件
app.use(router)          // 路由
app.use(createPinia())   // 状态管理
app.use(vuetify)         // Vuetify
app.use(VueAxios, axios) // VueAxios

// app.config.productionTip = false
//
// const api = axios.create({
//   baseURL: process.env.VUE_APP_API_URL || 'http://localhost:8000/api',
//   timeout: 10000
// })
//
// // 请求拦截器
// api.interceptors.request.use(config => {
//   const token = localStorage.getItem('auth_token')
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`
//   }
//   return config
// }, error => {
//   return Promise.reject(error)
// })
//
// // 响应拦截器
// api.interceptors.response.use(response => {
//   return response.data
// }, error => {
//   if (error.response.status === 401) {
//     // 处理未授权
//     router.push('/login')
//   }
//   return Promise.reject(error)
// })
//
// app.prototype.$http = api
app.mount('#app')
