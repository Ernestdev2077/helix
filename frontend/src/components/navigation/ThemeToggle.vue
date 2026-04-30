<script setup lang="ts">
import { Monitor, Moon, Sun } from 'lucide-vue-next'
import { computed } from 'vue'

import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

const Icon = computed(() => {
  if (theme.mode === 'system') return Monitor
  if (theme.mode === 'dark') return Moon
  return Sun
})

const label = computed(() => {
  if (theme.mode === 'system') return 'System theme'
  if (theme.mode === 'dark') return 'Dark theme'
  return 'Light theme'
})
</script>

<template>
  <button
    class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    :title="`${label} (click to cycle)`"
    @click="theme.toggle()"
  >
    <component :is="Icon" :size="14" :stroke-width="1.75" />
  </button>
</template>
