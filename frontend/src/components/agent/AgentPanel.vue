<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import { CircleDollarSign, Cpu, Sparkles } from 'lucide-vue-next'

import type { AgentEvent } from '@/composables/useAgentStream'

defineProps<{ events?: AgentEvent[]; connected?: boolean; cost?: number; tokens?: number }>()
</script>

<template>
  <aside class="flex h-full flex-col border-l border-border bg-card/40">
    <div class="flex items-center justify-between border-b border-border px-4 py-3">
      <div class="flex items-center gap-2">
        <div
          class="flex h-6 w-6 items-center justify-center rounded-md bg-primary/15 text-primary"
          :class="{ 'animate-pulse-ring': connected }"
        >
          <Sparkles :size="13" />
        </div>
        <span class="text-sm font-medium">Agent timeline</span>
      </div>
      <span
        class="text-[10px] uppercase tracking-wide"
        :class="connected ? 'text-success' : 'text-muted-foreground'"
      >
        {{ connected ? 'live' : 'idle' }}
      </span>
    </div>

    <div class="flex-1 overflow-y-auto">
      <div v-if="!events || events.length === 0" class="p-6 text-xs text-muted-foreground">
        <p>No active run.</p>
        <p class="mt-1">Hit <span class="kbd">⌘</span><span class="kbd">↵</span> in the composer to start one.</p>
      </div>
      <ul v-else v-auto-animate class="px-4 py-3">
        <li
          v-for="e in events"
          :key="e.sequence"
          class="group relative flex gap-3 border-l border-border py-2 pl-4"
        >
          <span
            class="absolute left-[-3px] top-3 h-1.5 w-1.5 rounded-full bg-primary transition-transform group-hover:scale-125"
          />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-xs font-medium text-foreground">
                {{ e.node_name || e.kind }}
              </span>
              <span v-if="e.duration_ms" class="text-[10px] text-muted-foreground">
                {{ e.duration_ms }}ms
              </span>
            </div>
            <p class="mt-0.5 truncate text-xs text-muted-foreground">{{ e.message }}</p>
          </div>
        </li>
      </ul>
    </div>

    <footer class="grid grid-cols-2 gap-2 border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
      <div class="flex items-center gap-1.5">
        <Cpu :size="12" />
        <span>{{ tokens ?? 0 }} tok</span>
      </div>
      <div class="flex items-center gap-1.5 justify-end">
        <CircleDollarSign :size="12" />
        <span>${{ (cost ?? 0).toFixed(4) }}</span>
      </div>
    </footer>
  </aside>
</template>
