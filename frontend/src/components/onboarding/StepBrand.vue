<script setup lang="ts">
import { ArrowRight, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import { brandsApi, type Brand } from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const emit = defineEmits<{ next: [] }>()
const composer = useComposerStore()

const brand = ref<Brand | null>(null)
const name = ref('')
const description = ref('')
const audience = ref('')
const accent = ref('#7C3AED')
const voiceDo = ref<string[]>([])
const voiceDont = ref<string[]>([])
const newDo = ref('')
const newDont = ref('')

const submitting = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  if (composer.brands.length === 0) await composer.loadBrands()
  if (composer.brands.length > 0) {
    brand.value = composer.brands[0]
    name.value = brand.value.name
    description.value = brand.value.description
    audience.value = brand.value.target_audience
    accent.value = brand.value.accent_color || '#7C3AED'
    voiceDo.value = [...(brand.value.voice_do ?? [])]
    voiceDont.value = [...(brand.value.voice_dont ?? [])]
  }
})

function addDo() {
  if (newDo.value.trim()) {
    voiceDo.value.push(newDo.value.trim())
    newDo.value = ''
  }
}

function addDont() {
  if (newDont.value.trim()) {
    voiceDont.value.push(newDont.value.trim())
    newDont.value = ''
  }
}

async function submit() {
  if (!name.value.trim() || submitting.value) return
  submitting.value = true
  error.value = null
  try {
    const payload = {
      name: name.value.trim(),
      description: description.value.trim(),
      target_audience: audience.value.trim(),
      accent_color: accent.value,
      voice_do: voiceDo.value,
      voice_dont: voiceDont.value,
    }
    if (brand.value) {
      await brandsApi.update(brand.value.id, payload)
    } else {
      await brandsApi.create(payload)
    }
    await composer.loadBrands()
    emit('next')
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    error.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="space-y-5">
    <header>
      <h2 class="text-xl font-semibold tracking-tight">Brand basics</h2>
      <p class="mt-1 text-sm text-muted-foreground">
        Tell us what you're posting about and how you want to sound. The agents
        use this on every Run.
      </p>
    </header>

    <div class="grid gap-4">
      <label class="block">
        <span class="mb-1.5 block text-xs text-muted-foreground">Brand / product name</span>
        <input
          v-model="name"
          type="text"
          placeholder="e.g. helix"
          class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
      </label>

      <label class="block">
        <span class="mb-1.5 block text-xs text-muted-foreground">One-line description</span>
        <input
          v-model="description"
          type="text"
          placeholder="An agent-native SMM workspace for indie devs"
          class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
      </label>

      <label class="block">
        <span class="mb-1.5 block text-xs text-muted-foreground">Target audience</span>
        <input
          v-model="audience"
          type="text"
          placeholder="Indie hackers, dev-tool founders, B2B SaaS marketers"
          class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        />
      </label>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <span class="mb-1.5 block text-xs text-muted-foreground">Voice DO</span>
          <div class="flex flex-wrap items-center gap-1.5 rounded-md border border-border bg-input/40 p-2">
            <span
              v-for="(t, i) in voiceDo"
              :key="t"
              class="inline-flex h-6 items-center gap-1 rounded-full border border-success/30 bg-success/10 px-2 text-[11px] text-success"
            >
              {{ t }}
              <button class="opacity-60 hover:opacity-100" @click="voiceDo.splice(i, 1)">
                <X :size="10" />
              </button>
            </span>
            <input
              v-model="newDo"
              type="text"
              placeholder="add — concrete numbers"
              class="min-w-32 flex-1 bg-transparent px-1 text-xs focus:outline-none"
              @keydown.enter.prevent="addDo"
            />
          </div>
        </div>

        <div>
          <span class="mb-1.5 block text-xs text-muted-foreground">Voice DON'T</span>
          <div class="flex flex-wrap items-center gap-1.5 rounded-md border border-border bg-input/40 p-2">
            <span
              v-for="(t, i) in voiceDont"
              :key="t"
              class="inline-flex h-6 items-center gap-1 rounded-full border border-destructive/30 bg-destructive/10 px-2 text-[11px] text-destructive"
            >
              {{ t }}
              <button class="opacity-60 hover:opacity-100" @click="voiceDont.splice(i, 1)">
                <X :size="10" />
              </button>
            </span>
            <input
              v-model="newDont"
              type="text"
              placeholder="add — synergy"
              class="min-w-32 flex-1 bg-transparent px-1 text-xs focus:outline-none"
              @keydown.enter.prevent="addDont"
            />
          </div>
        </div>
      </div>

      <label class="flex items-center gap-3">
        <span class="text-xs text-muted-foreground">Accent color</span>
        <input
          v-model="accent"
          type="color"
          class="h-7 w-12 rounded border border-border bg-transparent"
        />
        <span class="font-mono text-[11px] text-muted-foreground">{{ accent }}</span>
      </label>
    </div>

    <p v-if="error" class="text-xs text-destructive">{{ error }}</p>

    <div class="flex justify-end">
      <button
        :disabled="!name.trim() || submitting"
        class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-all hover:brightness-110 disabled:opacity-50"
        @click="submit"
      >
        {{ submitting ? 'Saving…' : 'Continue' }}
        <ArrowRight :size="14" />
      </button>
    </div>
  </section>
</template>
