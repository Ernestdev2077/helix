<script setup lang="ts">
import {
  BarChart3,
  BookMarked,
  Calendar,
  Palette,
  Settings,
  Sparkles,
} from 'lucide-vue-next'
import { useRoute } from 'vue-router'

const route = useRoute()

const items = [
  { to: '/composer', icon: Sparkles, label: 'Composer' },
  { to: '/library', icon: BookMarked, label: 'Library' },
  { to: '/calendar', icon: Calendar, label: 'Calendar' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/brand', icon: Palette, label: 'Brand' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]
</script>

<template>
  <nav class="flex flex-col items-center gap-1 border-r border-border bg-muted/30 py-3">
    <router-link
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      :title="item.label"
      class="group relative flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      :class="{
        'bg-muted text-foreground shadow-sm': route.path.startsWith(item.to),
      }"
    >
      <component :is="item.icon" :size="18" :stroke-width="1.75" />
      <span
        class="pointer-events-none absolute left-full ml-2 rounded-md border border-border bg-card px-2 py-1 text-xs opacity-0 shadow-md transition-opacity group-hover:opacity-100"
      >
        {{ item.label }}
      </span>
    </router-link>
  </nav>
</template>
