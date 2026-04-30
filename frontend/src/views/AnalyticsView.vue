<script setup lang="ts">
import { TrendingDown, TrendingUp } from 'lucide-vue-next'

const kpis = [
  { label: 'Reach', value: '—', delta: null },
  { label: 'Engagement', value: '—', delta: null },
  { label: 'CTR', value: '—', delta: null },
]
</script>

<template>
  <div class="h-full overflow-y-auto px-8 py-6">
    <h1 class="mb-6 text-xl font-semibold tracking-tight">Analytics</h1>

    <div class="mb-6 grid grid-cols-3 gap-4">
      <article
        v-for="kpi in kpis"
        :key="kpi.label"
        class="rounded-lg border border-border bg-card p-4"
      >
        <p class="text-xs uppercase tracking-wide text-muted-foreground">{{ kpi.label }}</p>
        <div class="mt-1 flex items-baseline gap-2">
          <span class="text-2xl font-semibold tabular-nums">{{ kpi.value }}</span>
          <span
            v-if="kpi.delta"
            class="inline-flex items-center gap-0.5 text-xs"
            :class="kpi.delta > 0 ? 'text-success' : 'text-destructive'"
          >
            <TrendingUp v-if="kpi.delta > 0" :size="11" />
            <TrendingDown v-else :size="11" />
            {{ Math.abs(kpi.delta) }}%
          </span>
        </div>
      </article>
    </div>

    <div class="flex h-64 items-center justify-center rounded-lg border border-dashed border-border">
      <p class="text-sm text-muted-foreground">
        Charts appear once you publish your first posts.
      </p>
    </div>
  </div>
</template>
