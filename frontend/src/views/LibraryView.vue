<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import {
  BookMarked,
  Check,
  FileText,
  Lightbulb,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import {
  brandsCurateApi,
  kbDocumentsApi,
  referencesApi,
  styleRulesApi,
  type KBDocument,
  type Platform,
  type Reference,
  type ReferenceDNA,
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

const docs = ref<KBDocument[]>([])
const showDocForm = ref(false)
const docTitle = ref('')
const docText = ref('')
const docSubmitting = ref(false)
const docError = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    const [refs, ruleList, docList] = await Promise.all([
      referencesApi.list(),
      styleRulesApi.list(),
      kbDocumentsApi.list(),
    ])
    references.value = refs
    rules.value = ruleList
    docs.value = docList
  } finally {
    loading.value = false
  }
}

async function removeReference(id: string) {
  await referencesApi.remove(id)
  references.value = references.value.filter((r) => r.id !== id)
}

async function addDoc() {
  if (!docText.value.trim() || docSubmitting.value) return
  if (composer.brands.length === 0) await composer.loadBrands()
  const brand = composer.brands[0]
  if (!brand) {
    docError.value = 'Add a brand first'
    return
  }
  docSubmitting.value = true
  docError.value = null
  try {
    const doc = await kbDocumentsApi.paste({
      brand: brand.id,
      title: docTitle.value.trim() || 'Pasted note',
      raw_text: docText.value.trim(),
    })
    docs.value = [doc, ...docs.value]
    docTitle.value = ''
    docText.value = ''
    showDocForm.value = false
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    docError.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    docSubmitting.value = false
  }
}

async function removeDoc(id: string) {
  await kbDocumentsApi.remove(id)
  docs.value = docs.value.filter((d) => d.id !== id)
}

async function approveRule(id: string) {
  const updated = await styleRulesApi.approve(id)
  rules.value = rules.value.map((r) => (r.id === id ? updated : r))
}

async function rejectRule(id: string) {
  const updated = await styleRulesApi.reject(id)
  rules.value = rules.value.map((r) => (r.id === id ? updated : r))
}

function hasDna(dna: ReferenceDNA | null | undefined): boolean {
  if (!dna || typeof dna !== 'object') return false
  return Boolean(dna.tone || dna.structure || dna.hook_patterns || (dna.style_rules?.length ?? 0))
}

async function reExtractDna(id: string) {
  try {
    await referencesApi.extractDna(id)
    setTimeout(() => void load(), 6000)
  } catch (err) {
    console.warn('extractDna failed', err)
  }
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
          class="group relative rounded-lg border border-border bg-card p-4"
        >
          <button
            class="absolute right-2 top-2 hidden rounded p-1 text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive group-hover:block"
            title="Remove reference"
            @click="removeReference(ref.id)"
          >
            <Trash2 :size="11" />
          </button>
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

          <!-- Reference DNA: extracted automatically by the agent -->
          <div class="mt-3 border-t border-border pt-3 text-[11px]">
            <div
              v-if="!hasDna(ref.extracted_features)"
              class="flex items-center gap-1.5 text-muted-foreground"
            >
              <Sparkles :size="11" class="animate-pulse" />
              <span>Extracting DNA…</span>
              <button
                class="ml-auto opacity-0 transition-opacity hover:underline group-hover:opacity-100"
                @click="reExtractDna(ref.id)"
              >
                retry
              </button>
            </div>
            <div v-else class="space-y-1">
              <div class="flex items-center gap-1.5 font-medium text-foreground">
                <Sparkles :size="11" class="text-primary" />
                <span>Writing DNA</span>
              </div>
              <p v-if="ref.extracted_features.tone" class="text-muted-foreground">
                <span class="text-foreground/70">Tone:</span>
                {{ ref.extracted_features.tone }}
              </p>
              <p v-if="ref.extracted_features.hook_patterns" class="text-muted-foreground">
                <span class="text-foreground/70">Hook:</span>
                {{ ref.extracted_features.hook_patterns }}
              </p>
              <p v-if="ref.extracted_features.structure" class="text-muted-foreground">
                <span class="text-foreground/70">Structure:</span>
                {{ ref.extracted_features.structure }}
              </p>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- Knowledge documents -->
    <section class="mt-10">
      <header class="mb-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <FileText :size="14" />
          <h2 class="text-sm font-medium">Knowledge documents</h2>
          <span class="text-xs text-muted-foreground">({{ docs.length }})</span>
        </div>
        <button
          class="inline-flex h-7 items-center gap-1 rounded-md border border-border px-2 text-[11px] hover:bg-muted"
          @click="showDocForm = !showDocForm"
        >
          <Plus :size="11" />
          {{ showDocForm ? 'Cancel' : 'Add doc' }}
        </button>
      </header>

      <div v-if="showDocForm" class="mb-4 rounded-lg border border-border bg-card p-4">
        <input
          v-model="docTitle"
          type="text"
          placeholder="Title (optional)"
          class="mb-2 w-full rounded-md border border-border bg-input/40 px-3 py-2 text-xs focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
        <textarea
          v-model="docText"
          rows="5"
          placeholder="Paste landing page copy, README, or product overview. Chunked + embedded synchronously."
          class="w-full resize-none rounded-md border border-border bg-input/40 p-3 text-xs leading-relaxed focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
        <p v-if="docError" class="mt-2 text-xs text-destructive">{{ docError }}</p>
        <div class="mt-2 flex justify-end">
          <button
            :disabled="!docText.trim() || docSubmitting"
            class="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:brightness-110 disabled:opacity-50"
            @click="addDoc"
          >
            <Loader2 v-if="docSubmitting" :size="11" class="animate-spin" />
            {{ docSubmitting ? 'Indexing…' : 'Add' }}
          </button>
        </div>
      </div>

      <div
        v-if="docs.length === 0 && !loading"
        class="flex h-32 flex-col items-center justify-center rounded-lg border-2 border-dashed border-border text-center"
      >
        <FileText :size="20" class="text-muted-foreground" />
        <p class="mt-2 text-xs text-muted-foreground">
          No knowledge yet. Drop product docs here so writers always have brand context.
        </p>
      </div>
      <ul v-else v-auto-animate class="grid gap-2">
        <li
          v-for="d in docs"
          :key="d.id"
          class="group flex items-center justify-between gap-3 rounded-md border border-border bg-card px-4 py-3"
        >
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium">{{ d.title }}</p>
            <p class="text-[11px] text-muted-foreground">
              {{ d.source_type }} · {{ d.token_count }} tokens · status
              <span
                :class="
                  d.status === 'ready'
                    ? 'text-success'
                    : d.status === 'failed'
                    ? 'text-destructive'
                    : 'text-muted-foreground'
                "
              >
                {{ d.status }}
              </span>
            </p>
          </div>
          <button
            class="opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
            title="Remove document"
            @click="removeDoc(d.id)"
          >
            <Trash2 :size="13" />
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>
