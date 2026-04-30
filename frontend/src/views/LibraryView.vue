<script setup lang="ts">
import { BookMarked, Check, Lightbulb, Plus, X } from 'lucide-vue-next'
import { ref } from 'vue'

import type { StyleRule } from '@/api/resources'

const activeTab = ref<'all' | 'x' | 'reddit' | 'linkedin'>('all')

const proposedRules = ref<Partial<StyleRule>[]>([
  {
    id: 'demo-1',
    platform: 'x',
    rule_text: 'Open with a concrete number in line one',
    rationale: 'Extracted from 7 liked references and 3 A/B winners with +43% engagement.',
    confidence: 0.82,
    status: 'proposed',
  },
])

const activeRules = ref<Partial<StyleRule>[]>([
  {
    id: 'demo-2',
    scope: 'global',
    rule_text: 'Avoid buzzwords: synergy, leverage, unlock, empower',
    confidence: 0.95,
    status: 'approved',
  },
])
</script>

<template>
  <div class="h-full overflow-y-auto px-8 py-6">
    <header class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Library</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          References the model learns from — your liked posts and A/B winners.
        </p>
      </div>
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow-sm transition-all hover:brightness-110"
      >
        <Plus :size="12" />
        Add reference
      </button>
    </header>

    <!-- Tabs -->
    <div class="mb-4 flex items-center gap-1 border-b border-border">
      <button
        v-for="tab in (['all', 'x', 'reddit', 'linkedin'] as const)"
        :key="tab"
        class="relative flex h-9 items-center gap-2 px-3 text-xs capitalize transition-colors"
        :class="
          activeTab === tab ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
        "
        @click="activeTab = tab"
      >
        {{ tab }}
        <span
          v-if="activeTab === tab"
          class="absolute inset-x-2 bottom-0 h-[2px] rounded-full bg-primary"
        />
      </button>
    </div>

    <!-- Style Rules learned -->
    <section class="mb-8">
      <div class="mb-3 flex items-center gap-2">
        <Lightbulb :size="14" class="text-warn" />
        <h2 class="text-sm font-medium">Style rules learned</h2>
      </div>
      <div class="grid gap-3">
        <article
          v-for="rule in proposedRules"
          :key="rule.id"
          class="rounded-lg border border-warn/40 bg-warn/5 p-4"
        >
          <div class="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wide">
            <span class="rounded bg-warn/20 px-1.5 py-0.5 text-warn">proposed</span>
            <span class="text-muted-foreground">{{ rule.platform }} · confidence {{ rule.confidence }}</span>
          </div>
          <p class="text-sm font-medium">"{{ rule.rule_text }}"</p>
          <p class="mt-1 text-xs text-muted-foreground">{{ rule.rationale }}</p>
          <div class="mt-3 flex items-center gap-2">
            <button class="inline-flex h-7 items-center gap-1 rounded-md bg-primary px-2.5 text-xs text-primary-foreground hover:brightness-110">
              <Check :size="12" /> Approve
            </button>
            <button class="inline-flex h-7 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-muted">
              <X :size="12" /> Reject
            </button>
            <button class="text-xs text-muted-foreground hover:text-foreground">Edit</button>
          </div>
        </article>

        <article
          v-for="rule in activeRules"
          :key="rule.id"
          class="rounded-lg border border-border bg-card p-4"
        >
          <div class="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wide">
            <span class="rounded bg-success/20 px-1.5 py-0.5 text-success">active</span>
            <span class="text-muted-foreground">{{ rule.scope }} · confidence {{ rule.confidence }}</span>
          </div>
          <p class="text-sm">"{{ rule.rule_text }}"</p>
        </article>
      </div>
    </section>

    <!-- References grid -->
    <section>
      <h2 class="mb-3 text-sm font-medium">References</h2>
      <div
        class="flex h-48 flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-center"
      >
        <BookMarked :size="22" class="text-muted-foreground" />
        <p class="mt-2 text-sm text-muted-foreground">No references yet</p>
        <p class="mt-0.5 text-xs text-muted-foreground/70">
          Paste URLs of posts you like to start training your agents
        </p>
      </div>
    </section>
  </div>
</template>
