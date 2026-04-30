<script setup lang="ts">
import { Monitor, Moon, Settings, Sun } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useThemeStore, type ThemeMode } from '@/stores/theme'

const auth = useAuthStore()
const theme = useThemeStore()
const router = useRouter()

const themeOptions: { value: ThemeMode; label: string; icon: typeof Monitor }[] = [
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'light', label: 'Light', icon: Sun },
]

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

    <section class="mb-4 rounded-lg border border-border bg-card p-5">
      <h2 class="text-sm font-medium">Appearance</h2>
      <p class="mt-1 text-xs text-muted-foreground">
        Default is dark. System follows your OS preference.
      </p>
      <div class="mt-4 inline-flex rounded-md border border-border p-0.5">
        <button
          v-for="opt in themeOptions"
          :key="opt.value"
          class="inline-flex h-8 items-center gap-1.5 rounded px-3 text-xs font-medium transition-colors"
          :class="
            theme.mode === opt.value
              ? 'bg-muted text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          "
          @click="theme.set(opt.value)"
        >
          <component :is="opt.icon" :size="13" />
          {{ opt.label }}
        </button>
      </div>
      <p class="mt-3 text-[11px] text-muted-foreground">
        Currently using <span class="font-medium text-foreground">{{ theme.effective }}</span> theme.
      </p>
    </section>

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
