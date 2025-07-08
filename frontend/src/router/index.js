import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import LoginPage from '../views/LoginPage.vue'
import MainView from '../views/MainView.vue'
import RealVideoView from "@/views/RealVideoView.vue";
import CoordinateAlign from "@/views/CoordinateAlign.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
    },
    {
      path: '/',
      name: 'home',
      component: HomePage,
      children: [
        {
          path: '',
          name: 'main',
          component:MainView,
        },
        {
          path: 'realVideo',
          name: 'realVideo',
          component:RealVideoView,
        },
        {
          path: 'coordinate',
          name: 'coordinate',
          component:CoordinateAlign,
        },
        {
          path: 'about',
          name: 'about',
          // route level code-splitting
          // this generates a separate chunk (About.[hash].js) for this route
          // which is lazy-loaded when the route is visited.
          component: () => import('../views/AboutView.vue'),
        }
      ]
    },
  ],
})

export default router
