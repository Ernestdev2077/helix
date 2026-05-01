<script setup lang="ts">
import { Check } from 'lucide-vue-next'

defineProps<{
  steps: { id: number; label: string }[]
  current: number
}>()
</script>

<template>
  <nav class="flex items-center gap-2">
    <template v-for="(s, i) in steps" :key="s.id">
      <div class="flex items-center gap-2">
        <span
          class="flex h-7 w-7 items-center justify-center rounded-full border text-[11px] font-medium transition-all"
          :class="
            s.id < current
              ? 'border-primary bg-primary text-primary-foreground'
              : s.id === current
              ? 'border-primary text-primary ring-4 ring-primary/15'
              : 'border-border text-muted-foreground'
          "
        >
          <Check v-if="s.id < current" :size="13" />
          <span v-else>{{ s.id }}</span>
        </span>
        <span
          class="hidden text-xs sm:inline-block"
          :class="s.id <= current ? 'text-foreground' : 'text-muted-foreground'"
        >
          {{ s.label }}
        </span>
      </div>
      <span
        v-if="i < steps.length - 1"
        class="h-px flex-1 transition-colors"
        :class="s.id < current ? 'bg-primary' : 'bg-border'"
      />
    </template>
  </nav>
</template>
