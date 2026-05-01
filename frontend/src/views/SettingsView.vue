<script setup lang="ts">
import { CheckCircle2, Loader2, Monitor, Moon, Save, Settings, Sun } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useThemeStore, type ThemeMode } from '@/stores/theme'
import { useWorkspaceStore } from '@/stores/workspace'

const auth = useAuthStore()
const theme = useThemeStore()
const workspaces = useWorkspaceStore()
const router = useRouter()

const themeOptions: { value: ThemeMode; label: string; icon: typeof Monitor }[] = [
  { value: 'system', label: 'System', icon: Monitor },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'light', label: 'Light', icon: Sun },
]

const wsName = ref('')
const wsSaving = ref(false)
const wsSaved = ref(false)
const wsError = ref<string | null>(null)

const ws = computed(() => workspaces.activeWorkspace)
const wsDirty = computed(() => ws.value && wsName.value.trim() !== ws.value.name)

onMounted(async () => {
  if (workspaces.workspaces.length === 0) await workspaces.load()
  if (ws.value) wsName.value = ws.value.name
})

async function saveWorkspace() {
  if (!ws.value || !wsDirty.value || wsSaving.value) return
  wsSaving.value = true
  wsError.value = null
  try {
    await workspaces.update(ws.value.id, { name: wsName.value.trim() })
    wsSaved.value = true
    setTimeout(() => (wsSaved.value = false), 1800)
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    wsError.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    wsSaving.value = false
  }
}

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

    <!-- Workspace -->
    <section class="mb-4 rounded-lg border border-border bg-card p-5">
      <header class="mb-3 flex items-center justify-between">
        <div>
          <h2 class="text-sm font-medium">Workspace</h2>
          <p v-if="ws" class="mt-0.5 text-xs text-muted-foreground">
            {{ ws.plan }} · {{ ws.ai_credits_used }} / {{ ws.ai_credits_monthly }} AI credits used
          </p>
        </div>
        <span v-if="wsSaved" class="flex items-center gap-1 text-xs text-success">
          <CheckCircle2 :size="13" />
          Saved
        </span>
      </header>

      <label class="block">
        <span class="mb-1.5 block text-xs text-muted-foreground">Name</span>
        <div class="flex items-center gap-2">
          <input
            v-model="wsName"
            type="text"
            class="flex-1 rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
            @keydown.enter.prevent="saveWorkspace"
          />
          <button
            :disabled="!wsDirty || wsSaving"
            class="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:brightness-110 disabled:opacity-50"
            @click="saveWorkspace"
          >
            <Loader2 v-if="wsSaving" :size="13" class="animate-spin" />
            <Save v-else :size="13" />
            {{ wsSaving ? 'Saving…' : 'Save' }}
          </button>
        </div>
      </label>
      <p v-if="ws" class="mt-2 text-[11px] text-muted-foreground">
        Slug <span class="font-mono">{{ ws.slug }}</span> · ID
        <span class="font-mono">{{ ws.id.slice(0, 8) }}</span>
      </p>
      <p v-if="wsError" class="mt-2 text-xs text-destructive">{{ wsError }}</p>
    </section>

    <!-- Appearance -->
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

    <!-- Account -->
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
