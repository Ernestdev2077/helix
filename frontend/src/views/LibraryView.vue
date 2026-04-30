<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import { BookMarked, Check, Lightbulb, Sparkles, X } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import {
  brandsCurateApi,
  referencesApi,
  styleRulesApi,
  type Platform,
  type Reference,
  type StyleRule,
} from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const composer = useComposerStore()

const activeTab = ref<'all' | Platform>('all')
const references = ref<Reference[]>([])
const rules = ref<StyleRule[]>([])
const loading = ref(false)
const curating = ref(false)
const message = ref<string | null>(null)

const filteredRefs = computed(() =>
  activeTab.value === 'all'
    ? references.value
    : references.value.filter((r) => r.platform === activeTab.value),
)

const proposedRules = computed(() => rules.value.filter((r) => r.status === 'proposed'))
const activeRules = computed(() => rules.value.filter((r) => r.status === 'approved'))

async function load() {
  loading.value = true
  try {
    const [refs, ruleList] = await Promise.all([referencesApi.list(), styleRulesApi.list()])
    references.value = refs
    rules.value = ruleList
  } finally {
    loading.value = false
  }
}

async function approveRule(id: string) {
  const updated = await styleRulesApi.approve(id)
  rules.value = rules.value.map((r) => (r.id === id ? updated : r))
}

async function rejectRule(id: string) {
  const updated = await styleRulesApi.reject(id)
  rules.value = rules.value.map((r) => (r.id === id ? updated : r))
}

async function runCurator() {
  if (composer.brands.length === 0) await composer.loadBrands()
  const brand = composer.brands.find((b) => b.id === composer.activeBrandId) ?? composer.brands[0]
  if (!brand) {
    message.value = 'No brand. Run `seed_demo` first.'
    return
  }
  curating.value = true
  message.value = null
  try {
    await brandsCurateApi.curate(brand.id)
    message.value = 'Curator started. Refresh in 5–15s to see proposed rules.'
    setTimeout(() => void load(), 8000)
  } catch (err) {
    const e = err as { message?: string }
    message.value = e.message ?? 'Curator failed'
  } finally {
    curating.value = false
  }
}

onMounted(load)
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
        class="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow-sm transition-all hover:brightness-110 disabled:opacity-50"
        :disabled="curating"
        @click="runCurator"
      >
        <Sparkles :size="12" />
        {{ curating ? 'Running…' : 'Run Curator' }}
      </button>
    </header>
    <p v-if="message" class="mb-4 rounded border border-border bg-card px-3 py-2 text-xs">
      {{ message }}
    </p>

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

    <section class="mb-8">
      <div class="mb-3 flex items-center gap-2">
        <Lightbulb :size="14" class="text-warn" />
        <h2 class="text-sm font-medium">Style rules learned</h2>
        <span class="text-xs text-muted-foreground">
          ({{ proposedRules.length }} proposed · {{ activeRules.length }} active)
        </span>
      </div>
      <div v-auto-animate class="grid gap-3">
        <article
          v-for="rule in proposedRules"
          :key="rule.id"
          class="rounded-lg border border-warn/40 bg-warn/5 p-4"
        >
          <div class="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wide">
            <span class="rounded bg-warn/20 px-1.5 py-0.5 text-warn">proposed</span>
            <span class="text-muted-foreground">
              {{ rule.scope }}{{ rule.platform ? ' · ' + rule.platform : '' }} · confidence
              {{ rule.confidence.toFixed(2) }}
            </span>
          </div>
          <p class="text-sm font-medium">"{{ rule.rule_text }}"</p>
          <p v-if="rule.rationale" class="mt-1 text-xs text-muted-foreground">
            {{ rule.rationale }}
          </p>
          <div class="mt-3 flex items-center gap-2">
            <button
              class="inline-flex h-7 items-center gap-1 rounded-md bg-primary px-2.5 text-xs text-primary-foreground hover:brightness-110"
              @click="approveRule(rule.id)"
            >
              <Check :size="12" /> Approve
            </button>
            <button
              class="inline-flex h-7 items-center gap-1 rounded-md border border-border px-2.5 text-xs hover:bg-muted"
              @click="rejectRule(rule.id)"
            >
              <X :size="12" /> Reject
            </button>
          </div>
        </article>

        <article
          v-for="rule in activeRules"
          :key="rule.id"
          class="rounded-lg border border-border bg-card p-4"
        >
          <div class="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wide">
            <span class="rounded bg-success/20 px-1.5 py-0.5 text-success">active</span>
            <span class="text-muted-foreground">
              {{ rule.scope }}{{ rule.platform ? ' · ' + rule.platform : '' }}
            </span>
          </div>
          <p class="text-sm">"{{ rule.rule_text }}"</p>
        </article>

        <div
          v-if="proposedRules.length === 0 && activeRules.length === 0"
          class="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground"
        >
          No style rules yet. Star a few variants in the Composer, then click "Run Curator".
        </div>
      </div>
    </section>

    <section>
      <h2 class="mb-3 text-sm font-medium">References ({{ filteredRefs.length }})</h2>
      <div
        v-if="loading"
        class="flex h-32 items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted-foreground"
      >
        Loading…
      </div>
      <div
        v-else-if="filteredRefs.length === 0"
        class="flex h-48 flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-center"
      >
        <BookMarked :size="22" class="text-muted-foreground" />
        <p class="mt-2 text-sm text-muted-foreground">No references for this filter</p>
        <p class="mt-0.5 text-xs text-muted-foreground/70">
          Star variants in the Composer to grow the library
        </p>
      </div>
      <div v-else v-auto-animate class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="ref in filteredRefs"
          :key="ref.id"
          class="rounded-lg border border-border bg-card p-4"
        >
          <div class="mb-2 flex items-center justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
            <span class="rounded bg-muted px-1.5 py-0.5">{{ ref.platform }}</span>
            <span v-if="ref.source">{{ ref.source }}</span>
          </div>
          <p class="line-clamp-6 whitespace-pre-wrap text-xs leading-relaxed">{{ ref.raw_text }}</p>
          <div v-if="ref.tags.length" class="mt-2 flex flex-wrap gap-1">
            <span
              v-for="t in ref.tags"
              :key="t"
              class="rounded bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              #{{ t }}
            </span>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
