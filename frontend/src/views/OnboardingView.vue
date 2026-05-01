<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import StepBrand from '@/components/onboarding/StepBrand.vue'
import StepConnect from '@/components/onboarding/StepConnect.vue'
import StepDemo from '@/components/onboarding/StepDemo.vue'
import StepSeed from '@/components/onboarding/StepSeed.vue'
import StepWorkspace from '@/components/onboarding/StepWorkspace.vue'
import Stepper from '@/components/onboarding/Stepper.vue'
import { useComposerStore } from '@/stores/composer'
import { useWorkspaceStore } from '@/stores/workspace'

const route = useRoute()
const router = useRouter()
const workspaces = useWorkspaceStore()
const composer = useComposerStore()

const STEPS = [
  { id: 1, label: 'Workspace' },
  { id: 2, label: 'Connect' },
  { id: 3, label: 'Brand' },
  { id: 4, label: 'Seed' },
  { id: 5, label: 'Demo' },
]

const currentStep = ref(1)

function next() {
  currentStep.value = Math.min(STEPS.length, currentStep.value + 1)
  void router.replace({ query: { ...route.query, step: String(currentStep.value) } })
}

function done() {
  void router.push({ name: 'composer' })
}

function jumpTo(step: number) {
  currentStep.value = Math.max(1, Math.min(STEPS.length, step))
}

onMounted(async () => {
  // 1) Resume from query string (e.g. after OAuth callback)
  const qStep = Number(route.query.step)
  if (qStep && qStep >= 1 && qStep <= STEPS.length) {
    jumpTo(qStep)
    return
  }

  // 2) Resume from data: skip steps user has already completed
  await workspaces.load()
  if (workspaces.workspaces.length === 0) {
    jumpTo(1)
    return
  }
  await composer.loadBrands()
  if (composer.brands.length === 0) {
    jumpTo(2) // workspace done, go to Connect
    return
  }
  // Workspace + brand exist — they probably came back to keep going
  jumpTo(4)
})
</script>

<template>
  <div class="min-h-screen bg-background">
    <header class="border-b border-border px-6 py-4">
      <div class="mx-auto flex max-w-3xl items-center gap-3">
        <span class="text-base">🧬</span>
        <span class="text-sm font-semibold tracking-tight">helix</span>
        <span class="text-muted-foreground/40">/</span>
        <span class="text-sm text-muted-foreground">setup</span>
        <button
          class="ml-auto text-xs text-muted-foreground hover:text-foreground"
          @click="done"
        >
          Skip onboarding
        </button>
      </div>
    </header>

    <main class="mx-auto w-full max-w-3xl px-6 py-10">
      <div class="mb-10">
        <Stepper :steps="STEPS" :current="currentStep" />
      </div>

      <div class="rounded-xl border border-border bg-card p-8">
        <Transition name="fade" mode="out-in">
          <StepWorkspace v-if="currentStep === 1" key="1" @next="next" />
          <StepConnect v-else-if="currentStep === 2" key="2" @next="next" @skip="next" />
          <StepBrand v-else-if="currentStep === 3" key="3" @next="next" />
          <StepSeed v-else-if="currentStep === 4" key="4" @next="next" @skip="next" />
          <StepDemo v-else-if="currentStep === 5" key="5" @done="done" />
        </Transition>
      </div>

      <p class="mt-6 flex items-center justify-center gap-1.5 text-center text-xs text-muted-foreground">
        <Sparkles :size="11" />
        helix learns from every star, like, and reference. The more you feed it, the more it sounds like you.
      </p>
    </main>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 200ms cubic-bezier(0.22, 1, 0.36, 1);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
