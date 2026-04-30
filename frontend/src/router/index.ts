import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/composer' },
      {
        path: 'composer',
        name: 'composer',
        component: () => import('@/views/ComposerView.vue'),
        meta: { title: 'Composer' },
      },
      {
        path: 'library',
        name: 'library',
        component: () => import('@/views/LibraryView.vue'),
        meta: { title: 'Library' },
      },
      {
        path: 'calendar',
        name: 'calendar',
        component: () => import('@/views/CalendarView.vue'),
        meta: { title: 'Calendar' },
      },
      {
        path: 'analytics',
        name: 'analytics',
        component: () => import('@/views/AnalyticsView.vue'),
        meta: { title: 'Analytics' },
      },
      {
        path: 'brand',
        name: 'brand',
        component: () => import('@/views/BrandView.vue'),
        meta: { title: 'Brand' },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: 'Settings' },
      },
    ],
  },
  {
    path: '/auth',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      {
        path: 'login',
        name: 'login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: { title: 'Sign in' },
      },
      {
        path: 'signup',
        name: 'signup',
        component: () => import('@/views/auth/SignupView.vue'),
        meta: { title: 'Sign up' },
      },
    ],
  },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('@/views/OnboardingView.vue'),
    meta: { requiresAuth: true, title: 'Welcome' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.title) {
    document.title = `${to.meta.title as string} · helix`
  } else {
    document.title = 'helix'
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if ((to.name === 'login' || to.name === 'signup') && auth.isAuthenticated) {
    return { name: 'composer' }
  }
  return true
})
