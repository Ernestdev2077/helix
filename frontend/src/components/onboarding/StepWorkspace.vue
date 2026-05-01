<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import { useWorkspaceStore } from '@/stores/workspace'

const emit = defineEmits<{ next: [] }>()
const workspaces = useWorkspaceStore()

const name = ref('')
const submitting = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  if (workspaces.workspaces.length === 0) await workspaces.load()
  if (workspaces.activeWorkspace) {
    name.value = workspaces.activeWorkspace.name
  }
})

async function submit() {
  if (!name.value.trim() || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    if (!workspaces.activeWorkspace) {
      await workspaces.create(name.value.trim())
    }
    emit('next')
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    error.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="space-y-5">
    <header>
      <h2 class="text-xl font-semibold tracking-tight">Name your workspace</h2>
      <p class="mt-1 text-sm text-muted-foreground">
        A workspace holds one or more brands, your team, and learnings. You can rename it later.
      </p>
    </header>

    <label class="block">
      <span class="mb-1.5 block text-xs text-muted-foreground">Workspace name</span>
      <input
        v-model="name"
        type="text"
        placeholder="e.g. Acme Inc."
        autofocus
        class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        @keydown.enter.prevent="submit"
      />
    </label>

    <p v-if="error" class="text-xs text-destructive">{{ error }}</p>

    <div class="flex justify-end">
      <button
        :disabled="!name.trim() || submitting"
        class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-all hover:brightness-110 disabled:opacity-50"
        @click="submit"
      >
        {{ submitting ? 'Creating…' : 'Continue' }}
        <ArrowRight :size="14" />
      </button>
    </div>
  </section>
</template>
