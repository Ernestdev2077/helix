<script setup lang="ts">
import axios from 'axios'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const email = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref('')

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const { data } = await axios.post(
      `${import.meta.env.VITE_API_URL || ''}/api/v1/auth/login/`,
      { email: email.value, password: password.value },
      { withCredentials: true },
    )
    auth.setSession(
      { access: data.access, refresh: data.refresh },
      data.user ? { ...data.user, full_name: data.user.full_name || '', avatar_url: '' } : undefined,
    )
    const next = (route.query.next as string) || '/composer'
    void router.push(next)
  } catch (err) {
    const e = err as { response?: { data?: { detail?: string } } }
    error.value = e.response?.data?.detail || 'Failed to sign in'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="space-y-4 rounded-lg border border-border bg-card p-6" @submit.prevent="submit">
    <h2 class="text-lg font-semibold">Sign in</h2>

    <label class="block">
      <span class="mb-1 block text-xs text-muted-foreground">Email</span>
      <input
        v-model="email"
        type="email"
        required
        class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none"
      />
    </label>

    <label class="block">
      <span class="mb-1 block text-xs text-muted-foreground">Password</span>
      <input
        v-model="password"
        type="password"
        required
        class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none"
      />
    </label>

    <p v-if="error" class="text-xs text-destructive">{{ error }}</p>

    <button
      type="submit"
      :disabled="submitting"
      class="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground disabled:opacity-50"
    >
      {{ submitting ? 'Signing in…' : 'Sign in' }}
    </button>

    <p class="text-center text-xs text-muted-foreground">
      No account?
      <router-link to="/auth/signup" class="text-primary hover:underline">Sign up</router-link>
    </p>
  </form>
</template>
