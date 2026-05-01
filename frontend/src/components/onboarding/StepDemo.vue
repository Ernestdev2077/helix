<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import {
  ArrowRight,
  CheckCircle2,
  Linkedin,
  MessageSquare,
  Play,
  Sparkles,
  Twitter,
} from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import type { Platform } from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const emit = defineEmits<{ done: [] }>()
const composer = useComposerStore()

const brief = ref('')
const platforms: Platform[] = ['x', 'reddit', 'linkedin']
const platformIcon = { x: Twitter, reddit: MessageSquare, linkedin: Linkedin } as const

const finalized = computed(() => {
  if (composer.events.length === 0) return false
  return composer.events.some(
    (e) => e.kind === 'node_finished' && (e.node_name === 'finalize' || e.node_name === 'ab_finalize'),
  )
})

const totalVariants = computed(() => composer.currentPost?.variants?.length ?? 0)

onMounted(async () => {
  if (composer.brands.length === 0) await composer.loadBrands()
  const brand = composer.brands[0]
  if (brand) {
    const audience = brand.target_audience ? ` Audience: ${brand.target_audience}.` : ''
    brief.value = `Launching ${brand.name} — ${brand.description}.${audience}`
  } else {
    brief.value = "Launching a small announcement — let's see what helix would write."
  }
})

async function run() {
  await composer.runBrief({
    brief: brief.value,
    platforms,
    goals: ['signups', 'brand'],
    toneHints: ['ironic', 'specific'],
  })
}

watch(finalized, (now) => {
  if (now) {
    // Best-effort: could auto-advance after a couple seconds. We let user click.
  }
})
</script>

<template>
  <section class="space-y-5">
    <header>
      <h2 class="text-xl font-semibold tracking-tight">First post — see helix in action</h2>
      <p class="mt-1 text-sm text-muted-foreground">
        We pre-filled a brief from your brand. Hit Run and watch 9 drafts (3 platforms x 3 hook
        strategies) appear in real time.
      </p>
    </header>

    <textarea
      v-model="brief"
      rows="3"
      class="w-full resize-none rounded-md border border-border bg-input/40 p-3 text-sm leading-relaxed focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
      :disabled="composer.generating"
    />

    <div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      <span>Platforms:</span>
      <span
        v-for="p in platforms"
        :key="p"
        class="inline-flex h-6 items-center gap-1 rounded-full border border-primary/40 bg-primary/10 px-2 text-[11px] text-primary"
      >
        <component :is="platformIcon[p]" :size="11" />
        {{ p }}
      </span>
    </div>

    <div v-if="!composer.events.length && !composer.generating" class="flex justify-center">
      <button
        :disabled="!brief.trim() || composer.generating"
        class="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground transition-all hover:brightness-110 disabled:opacity-50"
        @click="run"
      >
        <Play :size="14" />
        Run my first generation
      </button>
    </div>

    <div v-else>
      <div class="rounded-lg border border-border bg-card/40 p-4">
        <div class="mb-2 flex items-center gap-2 text-xs">
          <Sparkles
            :size="13"
            class="text-primary"
            :class="{ 'animate-pulse': composer.generating }"
          />
          <span class="font-medium">Agent timeline</span>
          <span
            v-if="finalized"
            class="ml-auto inline-flex items-center gap-1 text-success"
          >
            <CheckCircle2 :size="13" />
            Done — {{ totalVariants }} variants
          </span>
        </div>
        <ul v-auto-animate class="max-h-56 space-y-1 overflow-y-auto text-xs">
          <li v-for="e in composer.events" :key="e.sequence" class="flex gap-2">
            <span class="w-32 shrink-0 truncate text-muted-foreground">{{ e.node_name || e.kind }}</span>
            <span class="flex-1 text-foreground/80">{{ e.message }}</span>
          </li>
        </ul>
      </div>

      <div v-if="finalized" class="mt-5 rounded-lg border border-success/30 bg-success/5 p-4">
        <h3 class="text-sm font-medium">Your first {{ totalVariants }} drafts are ready.</h3>
        <p class="mt-1 text-xs text-muted-foreground">
          Open the Composer to review them, star your favorites, and try Refine ⚡ to iterate.
        </p>
        <button
          class="mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-all hover:brightness-110"
          @click="emit('done')"
        >
          Open in Composer
          <ArrowRight :size="14" />
        </button>
      </div>
    </div>
  </section>
</template>
