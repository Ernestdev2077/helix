<script setup lang="ts">
import {
  CheckCircle2,
  ExternalLink,
  Linkedin,
  Loader2,
  MessageSquare,
  Palette,
  Save,
  Twitter,
  Unplug,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import {
  brandsApi,
  oauthApi,
  platformAccountsApi,
  type Brand,
  type OAuthStatus,
  type PlatformAccount,
} from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const composer = useComposerStore()

const brand = ref<Brand | null>(null)
const name = ref('')
const description = ref('')
const audience = ref('')
const voiceDescription = ref('')
const accent = ref('#7C3AED')
const voiceDo = ref<string[]>([])
const voiceDont = ref<string[]>([])
const newDo = ref('')
const newDont = ref('')

const saving = ref(false)
const saveError = ref<string | null>(null)
const savedAt = ref<number | null>(null)

const oauthStatus = ref<OAuthStatus | null>(null)
const accounts = ref<PlatformAccount[]>([])

const dirty = computed(() => {
  if (!brand.value) return false
  return (
    name.value !== brand.value.name ||
    description.value !== (brand.value.description ?? '') ||
    audience.value !== (brand.value.target_audience ?? '') ||
    voiceDescription.value !== (brand.value.voice_description ?? '') ||
    accent.value !== (brand.value.accent_color || '#7C3AED') ||
    !sameArray(voiceDo.value, brand.value.voice_do ?? []) ||
    !sameArray(voiceDont.value, brand.value.voice_dont ?? [])
  )
})

function sameArray(a: string[], b: string[]) {
  if (a.length !== b.length) return false
  return a.every((v, i) => v === b[i])
}

function loadIntoForm(b: Brand) {
  brand.value = b
  name.value = b.name
  description.value = b.description ?? ''
  audience.value = b.target_audience ?? ''
  voiceDescription.value = b.voice_description ?? ''
  accent.value = b.accent_color || '#7C3AED'
  voiceDo.value = [...(b.voice_do ?? [])]
  voiceDont.value = [...(b.voice_dont ?? [])]
}

async function loadAll() {
  if (composer.brands.length === 0) await composer.loadBrands()
  if (composer.brands.length > 0) loadIntoForm(composer.brands[0])
  ;[oauthStatus.value, accounts.value] = await Promise.all([
    oauthApi.status(),
    platformAccountsApi.list(),
  ])
}

async function save() {
  if (!brand.value || !dirty.value || saving.value) return
  saving.value = true
  saveError.value = null
  try {
    const updated = await brandsApi.update(brand.value.id, {
      name: name.value.trim(),
      description: description.value.trim(),
      target_audience: audience.value.trim(),
      voice_description: voiceDescription.value.trim(),
      accent_color: accent.value,
      voice_do: voiceDo.value,
      voice_dont: voiceDont.value,
    })
    loadIntoForm(updated)
    await composer.loadBrands()
    savedAt.value = Date.now()
    setTimeout(() => {
      if (savedAt.value && Date.now() - savedAt.value > 1800) savedAt.value = null
    }, 2200)
  } catch (e) {
    const err = e as { response?: { data?: unknown }; message?: string }
    saveError.value = JSON.stringify(err.response?.data ?? err.message ?? e)
  } finally {
    saving.value = false
  }
}

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

function connectX() {
  window.location.href = '/api/v1/auth/oauth/x/start/'
}

async function disconnect(id: string) {
  await platformAccountsApi.disconnect(id)
  ;[oauthStatus.value, accounts.value] = await Promise.all([
    oauthApi.status(),
    platformAccountsApi.list(),
  ])
}

const xAccount = computed(() => accounts.value.find((a) => a.platform === 'x'))

onMounted(loadAll)
</script>

<template>
  <div class="mx-auto h-full max-w-3xl overflow-y-auto px-8 py-6">
    <header class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="flex items-center gap-2 text-xl font-semibold tracking-tight">
          <Palette :size="18" />
          Brand
        </h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Voice and tone, audience, connected accounts. Edit anything; agents will use the
          updated context on the next Run.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span
          v-if="savedAt"
          class="flex items-center gap-1 text-xs text-success"
        >
          <CheckCircle2 :size="13" />
          Saved
        </span>
        <button
          :disabled="!dirty || saving"
          class="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground transition-all hover:brightness-110 disabled:opacity-50"
          @click="save"
        >
          <Loader2 v-if="saving" :size="13" class="animate-spin" />
          <Save v-else :size="13" />
          {{ saving ? 'Saving…' : dirty ? 'Save changes' : 'Saved' }}
        </button>
      </div>
    </header>

    <p v-if="saveError" class="mb-4 rounded border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
      {{ saveError }}
    </p>

    <!-- Voice & Tone -->
    <section class="mb-4 rounded-lg border border-border bg-card p-5">
      <h2 class="text-sm font-medium">Voice and tone</h2>
      <p class="mt-1 text-xs text-muted-foreground">
        Used in every writer prompt. The Curator may also propose new rules over time.
      </p>

      <div class="mt-4 grid gap-4">
        <label class="block">
          <span class="mb-1.5 block text-xs text-muted-foreground">Brand / product name</span>
          <input
            v-model="name"
            type="text"
            class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
          />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-xs text-muted-foreground">One-line description</span>
          <input
            v-model="description"
            type="text"
            class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
          />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-xs text-muted-foreground">Target audience</span>
          <input
            v-model="audience"
            type="text"
            class="w-full rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
          />
        </label>
        <label class="block">
          <span class="mb-1.5 block text-xs text-muted-foreground">
            Voice description (free text — what tone, what feel)
          </span>
          <textarea
            v-model="voiceDescription"
            rows="2"
            placeholder="Confident, technical, irreverent. Talks to indie devs. Avoids corporate buzzwords."
            class="w-full resize-none rounded-md border border-border bg-input/40 px-3 py-2 text-sm focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
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
    </section>

    <!-- Connected accounts -->
    <section class="mb-4 rounded-lg border border-border bg-card p-5">
      <h2 class="text-sm font-medium">Connected accounts</h2>
      <p class="mt-1 text-xs text-muted-foreground">
        Disconnect to revoke tokens. Re-connect any time.
      </p>

      <div class="mt-4 grid gap-3">
        <article class="flex items-center justify-between gap-4 rounded-lg border border-border bg-background/40 p-3">
          <div class="flex items-center gap-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
              <Twitter :size="14" />
            </div>
            <div>
              <p class="text-sm font-medium">X (Twitter)</p>
              <p class="text-xs text-muted-foreground">
                <span v-if="xAccount">
                  <CheckCircle2 :size="11" class="inline text-success" />
                  Connected as @{{ xAccount.handle }}
                </span>
                <span v-else-if="oauthStatus?.x?.configured">Read-only OAuth</span>
                <span v-else>
                  Not configured.
                  <a
                    href="https://developer.twitter.com/en/portal/projects-and-apps"
                    target="_blank"
                    class="inline-flex items-center gap-0.5 text-foreground hover:underline"
                  >
                    Setup guide
                    <ExternalLink :size="9" />
                  </a>
                </span>
              </p>
            </div>
          </div>
          <button
            v-if="xAccount"
            class="inline-flex h-7 items-center gap-1 rounded-md border border-border px-2 text-[11px] hover:bg-muted"
            @click="disconnect(xAccount.id)"
          >
            <Unplug :size="11" />
            Disconnect
          </button>
          <button
            v-else-if="oauthStatus?.x?.configured"
            class="inline-flex h-7 items-center rounded-md bg-foreground px-2.5 text-[11px] font-medium text-background hover:opacity-90"
            @click="connectX"
          >
            Connect
          </button>
          <span v-else class="text-[10px] uppercase tracking-wide text-muted-foreground">setup needed</span>
        </article>

        <article class="flex items-center justify-between gap-4 rounded-lg border border-dashed border-border bg-muted/20 p-3 opacity-70">
          <div class="flex items-center gap-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
              <MessageSquare :size="14" />
            </div>
            <p class="text-sm font-medium">Reddit</p>
          </div>
          <span class="text-[10px] uppercase tracking-wide text-muted-foreground">soon</span>
        </article>
        <article class="flex items-center justify-between gap-4 rounded-lg border border-dashed border-border bg-muted/20 p-3 opacity-70">
          <div class="flex items-center gap-3">
            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
              <Linkedin :size="14" />
            </div>
            <p class="text-sm font-medium">LinkedIn</p>
          </div>
          <span class="text-[10px] uppercase tracking-wide text-muted-foreground">soon</span>
        </article>
      </div>
    </section>
  </div>
</template>
