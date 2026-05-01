<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import { ArrowRight, BookMarked, Heart, Loader2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import {
  kbDocumentsApi,
  referencesApi,
  type Platform,
  type Reference,
} from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const emit = defineEmits<{ next: []; skip: [] }>()
const composer = useComposerStore()

const tab = ref<'favorites' | 'knowledge'>('favorites')

// Favorites
const favoriteText = ref('')
const favoritePlatform = ref<Platform>('x')
const myRefs = ref<Reference[]>([])
const addingRef = ref(false)
const refError = ref<string | null>(null)

// Knowledge
const docTitle = ref('')
const docText = ref('')
const addingDoc = ref(false)
const docError = ref<string | null>(null)
const docCount = ref(0)

async function loadRefs() {
  myRefs.value = await referencesApi.list()
}

async function addFavorite() {
  if (!favoriteText.value.trim()) return
  if (composer.brands.length === 0) await composer.loadBrands()
  const brand = composer.brands[0]
  if (!brand) return

  addingRef.value = true
  refError.value = null
  try {
    await referencesApi.create({
      brand: brand.id,
      platform: favoritePlatform.value,
      raw_text: favoriteText.value.trim(),
      tags: ['onboarding'],
    })
    favoriteText.value = ''
    await loadRefs()
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    refError.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    addingRef.value = false
  }
}

async function addDoc() {
  if (!docText.value.trim()) return
  if (composer.brands.length === 0) await composer.loadBrands()
  const brand = composer.brands[0]
  if (!brand) return

  addingDoc.value = true
  docError.value = null
  try {
    await kbDocumentsApi.paste({
      brand: brand.id,
      title: docTitle.value.trim() || 'Pasted note',
      raw_text: docText.value.trim(),
    })
    docText.value = ''
    docTitle.value = ''
    docCount.value++
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    docError.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    addingDoc.value = false
  }
}

onMounted(() => void loadRefs())
</script>

<template>
  <section class="space-y-5">
    <header>
      <h2 class="text-xl font-semibold tracking-tight">Seed the model</h2>
      <p class="mt-1 text-sm text-muted-foreground">
        Drop 2-3 favorite posts (optional) and any reference docs about your product.
        The Curator will extract style DNA automatically.
      </p>
    </header>

    <div class="flex items-center gap-1 border-b border-border">
      <button
        class="relative flex h-9 items-center gap-2 px-3 text-xs transition-colors"
        :class="tab === 'favorites' ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'"
        @click="tab = 'favorites'"
      >
        <Heart :size="13" />
        Favorite posts
        <span class="rounded bg-muted px-1.5 py-0.5 text-[10px]">{{ myRefs.length }}</span>
        <span v-if="tab === 'favorites'" class="absolute inset-x-2 bottom-0 h-[2px] rounded-full bg-primary" />
      </button>
      <button
        class="relative flex h-9 items-center gap-2 px-3 text-xs transition-colors"
        :class="tab === 'knowledge' ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'"
        @click="tab = 'knowledge'"
      >
        <BookMarked :size="13" />
        Knowledge docs
        <span class="rounded bg-muted px-1.5 py-0.5 text-[10px]">{{ docCount }}</span>
        <span v-if="tab === 'knowledge'" class="absolute inset-x-2 bottom-0 h-[2px] rounded-full bg-primary" />
      </button>
    </div>

    <div v-if="tab === 'favorites'" class="space-y-3">
      <p class="text-xs text-muted-foreground">
        Paste posts you wish you had written. We'll extract their tone, structure, and hook patterns.
      </p>

      <div class="flex items-center gap-2">
        <label class="flex items-center gap-1.5 text-xs">
          <span class="text-muted-foreground">Platform</span>
          <select
            v-model="favoritePlatform"
            class="rounded-md border border-border bg-input/40 px-2 py-1 text-xs"
          >
            <option value="x">X</option>
            <option value="reddit">Reddit</option>
            <option value="linkedin">LinkedIn</option>
          </select>
        </label>
      </div>

      <textarea
        v-model="favoriteText"
        rows="4"
        placeholder="Paste a post you like — text only. Or copy-paste from any platform."
        class="w-full resize-none rounded-md border border-border bg-input/40 p-3 text-sm leading-relaxed focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
      />

      <p v-if="refError" class="text-xs text-destructive">{{ refError }}</p>

      <div class="flex justify-end">
        <button
          :disabled="!favoriteText.trim() || addingRef"
          class="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary/15 px-3 text-xs font-medium text-primary hover:bg-primary/25 disabled:opacity-50"
          @click="addFavorite"
        >
          <Loader2 v-if="addingRef" :size="11" class="animate-spin" />
          {{ addingRef ? 'Adding…' : 'Add favorite' }}
        </button>
      </div>

      <div v-if="myRefs.length > 0" v-auto-animate class="space-y-2">
        <article
          v-for="r in myRefs"
          :key="r.id"
          class="rounded-md border border-border bg-card p-3 text-xs"
        >
          <div class="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
            <span class="rounded bg-muted px-1.5 py-0.5">{{ r.platform }}</span>
            <span v-if="r.extracted_features?.tone">DNA: {{ r.extracted_features.tone }}</span>
            <span v-else class="italic">extracting DNA…</span>
          </div>
          <p class="line-clamp-3 whitespace-pre-wrap leading-relaxed">{{ r.raw_text }}</p>
        </article>
      </div>
    </div>

    <div v-else class="space-y-3">
      <p class="text-xs text-muted-foreground">
        Paste landing-page copy, README, blog posts, or any docs that describe your product.
        The agent will chunk and embed them so they show up as relevant context for every Run.
      </p>

      <input
        v-model="docTitle"
        type="text"
        placeholder="Title (optional)"
        class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
      />
      <textarea
        v-model="docText"
        rows="6"
        placeholder="Paste your doc here. Chunked + embedded synchronously — small docs take ~3-5 sec."
        class="w-full resize-none rounded-md border border-border bg-input/40 p-3 text-sm leading-relaxed focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
      />

      <p v-if="docError" class="text-xs text-destructive">{{ docError }}</p>

      <div class="flex justify-end">
        <button
          :disabled="!docText.trim() || addingDoc"
          class="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary/15 px-3 text-xs font-medium text-primary hover:bg-primary/25 disabled:opacity-50"
          @click="addDoc"
        >
          <Loader2 v-if="addingDoc" :size="11" class="animate-spin" />
          {{ addingDoc ? 'Chunking + embedding…' : 'Add knowledge' }}
        </button>
      </div>

      <p v-if="docCount > 0" class="text-xs text-muted-foreground">
        Added {{ docCount }} doc(s) — they're indexed and ready.
      </p>
    </div>

    <div class="flex items-center justify-between pt-2">
      <button
        class="text-xs text-muted-foreground hover:text-foreground"
        @click="emit('skip')"
      >
        Skip — I'll add later
      </button>
      <button
        class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-all hover:brightness-110"
        @click="emit('next')"
      >
        Continue
        <ArrowRight :size="14" />
      </button>
    </div>
  </section>
</template>
