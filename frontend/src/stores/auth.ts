import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export interface SessionUser {
  id: string
  email: string
  full_name: string
  avatar_url: string
}

const ACCESS_KEY = 'smm.access'
const REFRESH_KEY = 'smm.refresh'
const USER_KEY = 'smm.user'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(ACCESS_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<SessionUser | null>(
    JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  )

  const isAuthenticated = computed(() => !!accessToken.value)

  function setSession(tokens: { access: string; refresh?: string }, u?: SessionUser) {
    accessToken.value = tokens.access
    localStorage.setItem(ACCESS_KEY, tokens.access)
    if (tokens.refresh) {
      refreshToken.value = tokens.refresh
      localStorage.setItem(REFRESH_KEY, tokens.refresh)
    }
    if (u) {
      user.value = u
      localStorage.setItem(USER_KEY, JSON.stringify(u))
    }
  }

  async function clear() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    setSession,
    clear,
  }
})
