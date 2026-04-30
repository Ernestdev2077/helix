<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { computed } from 'vue'

import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

// Show the icon of the theme you'd switch TO (sun = "go light", moon = "go dark")
const Icon = computed(() => (theme.effective === 'dark' ? Sun : Moon))
const tip = computed(() =>
  theme.effective === 'dark' ? 'Switch to light theme' : 'Switch to dark theme',
)
</script>

<template>
  <button
    class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    :title="tip"
    @click="theme.toggle()"
  >
    <component :is="Icon" :size="14" :stroke-width="1.75" />
  </button>
</template>
