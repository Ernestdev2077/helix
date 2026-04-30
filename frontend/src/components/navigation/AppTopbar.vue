<script setup lang="ts">
import { ChevronsUpDown, Plus, Search } from 'lucide-vue-next'
import { computed } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { useWorkspaceStore } from '@/stores/workspace'

const auth = useAuthStore()
const workspaces = useWorkspaceStore()

const initial = computed(() =>
  auth.user?.email?.slice(0, 1).toUpperCase() ?? '?',
)
</script>

<template>
  <header
    class="flex items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-sm"
  >
    <div class="flex items-center gap-3">
      <button
        class="inline-flex items-center gap-2 rounded-md px-2.5 py-1 text-sm font-medium hover:bg-muted"
      >
        <span class="flex h-6 w-6 items-center justify-center rounded bg-primary text-[11px] font-semibold text-primary-foreground">
          {{ workspaces.activeWorkspace?.name?.slice(0, 2).toUpperCase() || 'SM' }}
        </span>
        <span class="text-foreground">{{ workspaces.activeWorkspace?.name || 'No workspace' }}</span>
        <ChevronsUpDown :size="14" class="text-muted-foreground" />
      </button>
    </div>

    <button
      class="flex h-7 w-64 items-center gap-2 rounded-md border border-border bg-muted/40 px-2.5 text-xs text-muted-foreground transition-colors hover:bg-muted"
    >
      <Search :size="13" />
      <span class="flex-1 text-left">Search or jump to</span>
      <span class="kbd">⌘</span><span class="kbd">P</span>
    </button>

    <div class="flex items-center gap-2">
      <button
        class="inline-flex h-7 items-center gap-1.5 rounded-md bg-primary px-2.5 text-xs font-medium text-primary-foreground shadow-sm transition-all hover:brightness-110 active:scale-[0.98]"
      >
        <Plus :size="13" />
        New post
      </button>
      <div
        class="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-medium"
        :title="auth.user?.email ?? ''"
      >
        {{ initial }}
      </div>
    </div>
  </header>
</template>
