<script setup lang="ts">
import { Settings } from 'lucide-vue-next'

import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

async function logout() {
  await auth.clear()
  void router.push({ name: 'login' })
}
</script>

<template>
  <div class="mx-auto h-full max-w-2xl overflow-y-auto px-8 py-6">
    <h1 class="mb-6 flex items-center gap-2 text-xl font-semibold tracking-tight">
      <Settings :size="18" /> Settings
    </h1>

    <section class="rounded-lg border border-border bg-card p-5">
      <h2 class="text-sm font-medium">Account</h2>
      <p class="mt-1 text-xs text-muted-foreground">{{ auth.user?.email || 'Not signed in' }}</p>
      <button
        class="mt-4 inline-flex h-8 items-center rounded-md border border-border px-3 text-xs hover:bg-muted"
        @click="logout"
      >
        Sign out
      </button>
    </section>
  </div>
</template>
