<script setup lang="ts">
import { vAutoAnimate } from '@formkit/auto-animate/vue'
import {
  Linkedin,
  MessageSquare,
  Play,
  Send,
  Sparkles,
  Star,
  Twitter,
  Zap,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

// import VariantImage from '@/components/composer/VariantImage.vue'  // hidden; focus on text features
import type { Platform } from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const composer = useComposerStore()

const brief = ref('')
const selectedPlatforms = ref<Platform[]>(['x', 'reddit', 'linkedin'])
const activePlatform = ref<Platform>('x')
const goals = ref<string[]>(['signups'])

const platformIcon = { x: Twitter, reddit: MessageSquare, linkedin: Linkedin } as const
const charLimit: Record<Platform, number> = { x: 280, reddit: 10000, linkedin: 3000 }

const activeVariants = computed(() => composer.variantsByPlatform[activePlatform.value] ?? [])

onMounted(() => {
  void composer.loadBrands()
})

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

async function runBrief() {
  if (!brief.value.trim() || composer.generating) return
  await composer.runBrief({
    brief: brief.value,
    platforms: selectedPlatforms.value,
    goals: goals.value,
  })
}

async function toggleStar(variantId: string, isStarred: boolean) {
  if (isStarred) {
    await composer.unstarVariant(variantId)
  } else {
    await composer.starVariant(variantId)
  }
}

async function refine(variantId: string) {
  await composer.refineVariant(variantId)
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
        :disabled="composer.generating"
        @keydown.meta.enter.prevent="runBrief"
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
            :disabled="composer.generating || !brief.trim()"
            class="inline-flex h-8 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow-sm transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
            @click="runBrief"
          >
            <Play :size="12" />
            {{ composer.generating ? 'Running...' : 'Run' }}
            <span class="kbd">⌘</span><span class="kbd">↵</span>
          </button>
        </div>
      </div>
      <p v-if="composer.error" class="mt-2 text-xs text-destructive">{{ composer.error }}</p>
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
          {{ composer.variantsByPlatform[p]?.length ?? 0 }}
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
          :class="{ 'animate-pulse-ring': composer.generating }"
        >
          <Sparkles :size="22" />
        </div>
        <h3 class="mt-4 text-base font-medium">
          {{ composer.generating ? 'Agents are drafting…' : 'No drafts yet' }}
        </h3>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ composer.generating
            ? 'Watch the timeline on the right — drafts will appear here as they complete.'
            : 'Describe what you want to post, hit ⌘↵. Agents will draft 3 variants per platform — each with a different hook strategy (curiosity / controversy / story).' }}
        </p>
      </div>

      <div v-else v-auto-animate class="mx-auto flex max-w-2xl flex-col gap-4">
        <article
          v-for="variant in activeVariants"
          :key="variant.id"
          class="group rounded-lg border bg-card p-5 transition-all"
          :class="
            variant.is_starred
              ? 'border-warn/60 ring-1 ring-warn/30'
              : 'border-border hover:border-primary/30'
          "
        >
          <header class="mb-3 flex items-center justify-between gap-2">
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <span class="inline-flex h-5 w-5 items-center justify-center rounded bg-muted font-medium">
                {{ variant.label }}
              </span>
              <span
                v-if="variant.hook_strategy"
                class="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary"
                :title="`Hook strategy: ${variant.hook_strategy}`"
              >
                {{ variant.hook_strategy }}
              </span>
              <span
                v-for="note in variant.critic_notes"
                :key="note.message"
                class="rounded px-1.5 py-0.5 text-[10px]"
                :class="
                  note.severity === 'error'
                    ? 'bg-destructive/15 text-destructive'
                    : 'bg-warn/15 text-warn'
                "
                :title="note.fix_suggestion ?? ''"
              >
                {{ note.message }}
              </span>
            </div>
            <div class="flex items-center gap-1">
              <button
                v-if="variant.is_starred"
                :disabled="composer.generating"
                class="inline-flex h-7 items-center gap-1 rounded-md bg-primary/15 px-2 text-[11px] font-medium text-primary transition-colors hover:bg-primary/25 disabled:opacity-50"
                :title="composer.generating ? 'Already running…' : 'Generate 3 reframings of this winner'"
                @click="refine(variant.id)"
              >
                <Zap :size="11" />
                Refine
              </button>
              <button
                class="rounded p-1 text-muted-foreground transition-colors hover:bg-muted"
                :class="{ 'text-warn': variant.is_starred }"
                :title="variant.is_starred ? 'Unstar' : 'Star as A/B winner'"
                @click="toggleStar(variant.id, variant.is_starred)"
              >
                <Star :size="14" :fill="variant.is_starred ? 'currentColor' : 'none'" />
              </button>
            </div>
          </header>
          <p class="whitespace-pre-wrap text-sm leading-relaxed">{{ variant.content }}</p>
          <!-- Image dropzone temporarily hidden — focus is on text features.
               Re-enable: <VariantImage :variant="variant" /> -->
          <footer class="mt-3 flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {{ variant.content.length }} / {{ charLimit[activePlatform] }} chars
            </span>
            <div class="flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
              <button
                class="inline-flex items-center gap-1 rounded bg-primary/15 px-2 py-1 font-medium text-primary hover:bg-primary/25"
                disabled
                title="Publishing not wired in MVP — star this variant to feed the learning loop"
              >
                <Send :size="11" />
                Publish (soon)
              </button>
            </div>
          </footer>
        </article>
      </div>
    </section>
  </div>
</template>
