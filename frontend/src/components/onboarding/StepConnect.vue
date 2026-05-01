<script setup lang="ts">
import { ArrowRight, CheckCircle2, ExternalLink, Linkedin, Twitter, MessageSquare } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import { oauthApi, type OAuthStatus } from '@/api/resources'

const emit = defineEmits<{ next: []; skip: [] }>()

const status = ref<OAuthStatus | null>(null)
const loading = ref(true)
const justConnected = ref<string | null>(null)

const connectedCount = computed(() => {
  if (!status.value) return 0
  return Object.values(status.value).filter((s) => s.connected).length
})

async function load() {
  loading.value = true
  try {
    status.value = await oauthApi.status()
  } finally {
    loading.value = false
  }
}

function connectX() {
  // Send the user to the backend OAuth start endpoint. It will set the PKCE
  // state in the session cookie and redirect to X. The callback eventually
  // redirects back to /onboarding?step=2&connected=x and we re-fetch status.
  window.location.href = '/api/v1/auth/oauth/x/start/'
}

onMounted(async () => {
  const params = new URLSearchParams(window.location.search)
  if (params.get('connected')) justConnected.value = params.get('connected')
  await load()
})
</script>

<template>
  <section class="space-y-5">
    <header>
      <h2 class="text-xl font-semibold tracking-tight">Connect a platform</h2>
      <p class="mt-1 text-sm text-muted-foreground">
        We'll publish, fetch metrics, and learn from real performance from here.
        Connect at least one to unlock real publishing later — or skip for now.
      </p>
    </header>

    <p
      v-if="justConnected === 'x' && status?.x?.connected"
      class="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-xs text-success"
    >
      Connected to X as <strong>@{{ status.x.handle }}</strong>.
    </p>

    <div v-if="loading" class="text-xs text-muted-foreground">Checking status…</div>

    <div v-else class="grid gap-3">
      <article class="flex items-center justify-between gap-4 rounded-lg border border-border bg-card p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-md bg-muted">
            <Twitter :size="16" />
          </div>
          <div>
            <p class="text-sm font-medium">X (Twitter)</p>
            <p class="text-xs text-muted-foreground">
              <span v-if="status?.x?.connected">
                <CheckCircle2 :size="11" class="inline text-success" />
                Connected as @{{ status.x.handle }}
              </span>
              <span v-else-if="status?.x?.configured">
                Read-only OAuth (publishing requires Basic API tier later)
              </span>
              <span v-else>
                OAuth app is not configured.
                <a
                  href="https://developer.twitter.com/en/portal/projects-and-apps"
                  target="_blank"
                  class="inline-flex items-center gap-0.5 text-foreground hover:underline"
                >
                  Setup guide
                  <ExternalLink :size="10" />
                </a>
              </span>
            </p>
          </div>
        </div>
        <button
          v-if="status?.x?.configured && !status?.x?.connected"
          class="inline-flex h-8 items-center rounded-md bg-foreground px-3 text-xs font-medium text-background hover:opacity-90"
          @click="connectX"
        >
          Connect
        </button>
        <span
          v-else-if="status?.x?.connected"
          class="text-[10px] uppercase tracking-wide text-success"
        >
          connected
        </span>
        <span
          v-else
          class="text-[10px] uppercase tracking-wide text-muted-foreground"
        >
          setup needed
        </span>
      </article>

      <article class="flex items-center justify-between gap-4 rounded-lg border border-dashed border-border bg-muted/30 p-4 opacity-70">
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-md bg-muted">
            <MessageSquare :size="16" />
          </div>
          <div>
            <p class="text-sm font-medium">Reddit</p>
            <p class="text-xs text-muted-foreground">Coming soon</p>
          </div>
        </div>
        <span class="text-[10px] uppercase tracking-wide text-muted-foreground">soon</span>
      </article>

      <article class="flex items-center justify-between gap-4 rounded-lg border border-dashed border-border bg-muted/30 p-4 opacity-70">
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-md bg-muted">
            <Linkedin :size="16" />
          </div>
          <div>
            <p class="text-sm font-medium">LinkedIn</p>
            <p class="text-xs text-muted-foreground">Coming soon</p>
          </div>
        </div>
        <span class="text-[10px] uppercase tracking-wide text-muted-foreground">soon</span>
      </article>
    </div>

    <div class="flex items-center justify-between pt-2">
      <button
        class="text-xs text-muted-foreground hover:text-foreground"
        @click="emit('skip')"
      >
        Skip for now
      </button>
      <button
        class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-all hover:brightness-110"
        @click="emit('next')"
      >
        {{ connectedCount > 0 ? 'Continue' : 'Continue without connecting' }}
        <ArrowRight :size="14" />
      </button>
    </div>
  </section>
</template>
