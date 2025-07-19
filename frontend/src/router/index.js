import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import LoginPage from '../views/LoginPage.vue'
import MainView from '../views/MainView.vue'
import RealVideoView from "@/views/RealVideoView.vue";
import CoordinateAlign from "@/views/CoordinateAlign.vue";
import ClassroomView from "@/views/ClassroomView.vue";
import StudentsView from "@/views/StudentsView.vue";
import AnalyticsView from "@/views/AnalyticsView.vue";
import testView from "@/views/testView.vue"

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
          path: 'test',
          name: 'test',
          component:testView,
        }
      ]
    },
    {
      path: '/classroom',
      name: 'classroom',
      component: ClassroomView,
    },
    {
      path: '/Students',
      name: 'students',
      component: StudentsView,
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: AnalyticsView,
    },
  ],
})

export default router
