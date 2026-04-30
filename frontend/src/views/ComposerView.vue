<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import { Linkedin, Play, Save, Send, Sparkles, Star, Twitter } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import type { Platform } from '@/api/resources'

const brief = ref('')
const selectedPlatforms = ref<Platform[]>(['x', 'reddit', 'linkedin'])
const activePlatform = ref<Platform>('x')
const goals = ref<string[]>(['signups'])
const generating = ref(false)

const variants = ref<Record<Platform, { label: string; content: string; starred: boolean }[]>>({
  x: [],
  reddit: [],
  linkedin: [],
})

const platformIcon = { x: Twitter, reddit: Sparkles, linkedin: Linkedin } as const

const charLimit: Record<Platform, number> = { x: 280, reddit: 10000, linkedin: 3000 }

const activeVariants = computed(() => variants.value[activePlatform.value])

function togglePlatform(p: Platform) {
  if (selectedPlatforms.value.includes(p)) {
    selectedPlatforms.value = selectedPlatforms.value.filter((x) => x !== p)
  } else {
    selectedPlatforms.value = [...selectedPlatforms.value, p]
  }
}

function addGoal(tag: string) {
  if (!goals.value.includes(tag)) goals.value.push(tag)
}

async function runGraph() {
  if (!brief.value.trim()) return
  generating.value = true
  try {
    // Placeholder — real call wires to postsApi.create + postsApi.generate
    // and subscribes the AgentPanel via useAgentStream(runId).
    await new Promise((r) => setTimeout(r, 700))
    for (const p of selectedPlatforms.value) {
      variants.value[p] = [
        {
          label: 'A',
          content: `[${p} draft for: ${brief.value.slice(0, 80)}]`,
          starred: false,
        },
      ]
    }
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <div class="flex h-full flex-col">
    <!-- Brief input -->
    <section class="border-b border-border px-8 py-6">
      <label class="mb-2 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Brief
      </label>
      <textarea
        v-model="brief"
        rows="3"
        placeholder="What are we posting about? e.g. Announcing feature X for indie devs, tone: ironic, no buzzwords"
        class="w-full resize-none rounded-md border border-border bg-input/40 p-3 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/70 focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        @keydown.meta.enter.prevent="runGraph"
      />
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <span class="text-xs text-muted-foreground">Platforms:</span>
        <button
          v-for="p in (['x', 'reddit', 'linkedin'] as Platform[])"
          :key="p"
          class="inline-flex h-6 items-center gap-1 rounded-full border px-2 text-[11px] transition-all"
          :class="
            selectedPlatforms.includes(p)
              ? 'border-primary/50 bg-primary/10 text-primary'
              : 'border-border bg-muted/40 text-muted-foreground hover:bg-muted'
          "
          @click="togglePlatform(p)"
        >
          <component :is="platformIcon[p]" :size="11" />
          {{ p }}
        </button>

        <span class="ml-4 text-xs text-muted-foreground">Goals:</span>
        <span
          v-for="g in goals"
          :key="g"
          class="inline-flex h-6 items-center rounded-full border border-border bg-muted/40 px-2 text-[11px]"
        >
          #{{ g }}
        </span>
        <button
          class="text-[11px] text-muted-foreground hover:text-foreground"
          @click="addGoal('brand')"
        >
          + add
        </button>

        <div class="ml-auto flex items-center gap-2">
          <button
            :disabled="generating || !brief.trim()"
            class="inline-flex h-8 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow-sm transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
            @click="runGraph"
          >
            <Play :size="12" />
            {{ generating ? 'Running...' : 'Run' }}
            <span class="kbd">⌘</span><span class="kbd">↵</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Platform tabs -->
    <section class="flex items-center gap-1 border-b border-border px-8">
      <button
        v-for="p in selectedPlatforms"
        :key="p"
        class="relative flex h-10 items-center gap-2 px-3 text-sm transition-colors"
        :class="
          activePlatform === p
            ? 'text-foreground'
            : 'text-muted-foreground hover:text-foreground'
        "
        @click="activePlatform = p"
      >
        <component :is="platformIcon[p]" :size="13" />
        {{ p }}
        <span
          class="inline-flex h-4 w-4 items-center justify-center rounded bg-muted text-[10px]"
        >
          {{ variants[p].length }}
        </span>
        <span
          v-if="activePlatform === p"
          class="absolute inset-x-2 bottom-0 h-[2px] rounded-full bg-primary"
        />
      </button>
    </section>

    <!-- Editor -->
    <section class="flex-1 overflow-y-auto px-8 py-6">
      <div v-if="activeVariants.length === 0" class="mx-auto max-w-2xl text-center">
        <div
          class="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary"
        >
          <Sparkles :size="22" />
        </div>
        <h3 class="mt-4 text-base font-medium">No drafts yet</h3>
        <p class="mt-1 text-sm text-muted-foreground">
          Describe what you want to post, hit <span class="kbd">⌘</span><span class="kbd">↵</span>,
          and the agents will draft across your selected platforms.
        </p>
      </div>

      <div v-else v-auto-animate class="mx-auto flex max-w-2xl flex-col gap-4">
        <article
          v-for="variant in activeVariants"
          :key="variant.label"
          class="group rounded-lg border border-border bg-card p-5 transition-all hover:border-primary/30"
        >
          <header class="mb-3 flex items-center justify-between">
            <div class="flex items-center gap-2 text-xs">
              <span class="inline-flex h-5 w-5 items-center justify-center rounded bg-muted font-medium">
                {{ variant.label }}
              </span>
              <span class="text-muted-foreground">variant</span>
            </div>
            <button
              class="rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-warn"
              :class="{ 'text-warn': variant.starred }"
              @click="variant.starred = !variant.starred"
            >
              <Star :size="14" :fill="variant.starred ? 'currentColor' : 'none'" />
            </button>
          </header>
          <p class="whitespace-pre-wrap text-sm leading-relaxed">{{ variant.content }}</p>
          <footer class="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {{ variant.content.length }} / {{ charLimit[activePlatform] }} chars
            </span>
            <div class="flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
              <button class="inline-flex items-center gap-1 rounded px-2 py-1 hover:bg-muted">
                <Save :size="11" />
                Save
              </button>
              <button
                class="inline-flex items-center gap-1 rounded bg-primary/15 px-2 py-1 font-medium text-primary hover:bg-primary/25"
              >
                <Send :size="11" />
                Publish
              </button>
            </div>
          </footer>
        </article>
      </div>
    </section>
  </div>
</template>
