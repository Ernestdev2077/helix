<script setup lang="ts">
import axios from 'axios'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const email = ref('')
const password1 = ref('')
const password2 = ref('')
const submitting = ref(false)
const error = ref('')

const auth = useAuthStore()
const router = useRouter()

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const { data } = await axios.post(
      `${import.meta.env.VITE_API_URL || ''}/api/v1/auth/registration/`,
      {
        email: email.value,
        password1: password1.value,
        password2: password2.value,
      },
      { withCredentials: true },
    )
    auth.setSession({ access: data.access, refresh: data.refresh }, data.user)
    void router.push('/onboarding')
  } catch (err) {
    const e = err as { response?: { data?: Record<string, string[]> } }
    const firstError = e.response?.data
      ? Object.values(e.response.data).flat()[0]
      : 'Failed to sign up'
    error.value = String(firstError)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="space-y-4 rounded-lg border border-border bg-card p-6" @submit.prevent="submit">
    <h2 class="text-lg font-semibold">Create account</h2>

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
        v-model="password1"
        type="password"
        required
        minlength="8"
        class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none"
      />
    </label>

    <label class="block">
      <span class="mb-1 block text-xs text-muted-foreground">Confirm password</span>
      <input
        v-model="password2"
        type="password"
        required
        minlength="8"
        class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none"
      />
    </label>

    <p v-if="error" class="text-xs text-destructive">{{ error }}</p>

    <button
      type="submit"
      :disabled="submitting"
      class="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary text-sm font-medium text-primary-foreground disabled:opacity-50"
    >
      {{ submitting ? 'Creating…' : 'Create account' }}
    </button>

    <p class="text-center text-xs text-muted-foreground">
      Already have an account?
      <router-link to="/auth/login" class="text-primary hover:underline">Sign in</router-link>
    </p>
  </form>
</template>
