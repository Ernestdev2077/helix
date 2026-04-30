import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import {
  brandsApi,
  mediaApi,
  postsApi,
  variantsApi,
  type Brand,
  type Platform,
  type Post,
  type PostVariant,
} from '@/api/resources'

import { useAuthStore } from './auth'
import { useWorkspaceStore } from './workspace'

/**
 * Build a base URL for WebSocket, with this priority:
 *   1. VITE_WS_URL (explicit override)
 *   2. VITE_API_URL with http→ws / https→wss
 *   3. Same-origin (relies on Vite dev proxy for /ws)
 */
function resolveWsBase(): string {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined
  if (explicit) return explicit.replace(/\/$/, '')

  const api = import.meta.env.VITE_API_URL as string | undefined
  if (api) {
    return api.replace(/^http(s?):/, (_, s) => `ws${s}:`).replace(/\/$/, '')
  }

  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}`
}

export interface AgentEvent {
  sequence: number
  kind: string
  node_name: string
  message: string
  data: Record<string, unknown>
  tokens_in?: number
  tokens_out?: number
  duration_ms?: number
  emitted_at?: number
}

export const useComposerStore = defineStore('composer', () => {
  const brands = ref<Brand[]>([])
  const activeBrandId = ref<string | null>(null)

  const currentPost = ref<Post | null>(null)
  const currentRunId = ref<string | null>(null)

  const events = ref<AgentEvent[]>([])
  const generating = ref(false)
  const error = ref<string | null>(null)

  let socket: WebSocket | null = null

  const variantsByPlatform = computed<Record<Platform, PostVariant[]>>(() => {
    const map: Record<Platform, PostVariant[]> = { x: [], reddit: [], linkedin: [] }
    if (!currentPost.value) return map
    for (const v of currentPost.value.variants ?? []) {
      map[v.platform]?.push(v)
    }
    return map
  })

  const totalTokens = computed(() =>
    events.value.reduce((sum, e) => sum + (e.tokens_in ?? 0) + (e.tokens_out ?? 0), 0),
  )

  async function loadBrands() {
    const items = await brandsApi.list()
    brands.value = items
    if (!activeBrandId.value && items.length > 0) {
      activeBrandId.value = items[0].id
    }
  }

  async function ensureBrand(): Promise<Brand | null> {
    if (brands.value.length === 0) await loadBrands()
    return brands.value.find((b) => b.id === activeBrandId.value) ?? brands.value[0] ?? null
  }

  function closeStream() {
    socket?.close()
    socket = null
  }

  function openStream(runId: string) {
    closeStream()
    events.value = []

    const auth = useAuthStore()
    const wsBase = resolveWsBase()
    // JWT in query string — browser WebSocket can't set Authorization header
    const tokenParam = auth.accessToken ? `?token=${encodeURIComponent(auth.accessToken)}` : ''
    const url = `${wsBase}/ws/agent-runs/${runId}/${tokenParam}`
    socket = new WebSocket(url)

    socket.onopen = () => {
      // server already authed us via the query param — nothing to send here
    }

    socket.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as AgentEvent & { type?: string }
        const exists = events.value.find((e) => e.sequence === payload.sequence)
        if (exists) return
        events.value = [...events.value, payload].sort((a, b) => a.sequence - b.sequence)

        if (
          payload.kind === 'node_finished' &&
          payload.node_name === 'finalize'
        ) {
          void refreshCurrentPost()
        }
      } catch {
        // swallow malformed frames
      }
    }
    socket.onclose = () => {
      // ok
    }
    socket.onerror = () => {
      error.value = 'Stream error'
    }
  }

  async function refreshCurrentPost() {
    if (!currentPost.value) return
    try {
      currentPost.value = await postsApi.get(currentPost.value.id)
    } catch (err) {
      console.warn('Failed to refresh post', err)
    } finally {
      generating.value = false
    }
  }

  async function runBrief(input: {
    brief: string
    platforms: Platform[]
    goals: string[]
    toneHints?: string[]
  }) {
    error.value = null
    generating.value = true

    const workspaces = useWorkspaceStore()
    if (!workspaces.activeWorkspaceId) await workspaces.load()
    const brand = await ensureBrand()
    if (!brand) {
      error.value = 'No brand found in this workspace. Run `seed_demo` first.'
      generating.value = false
      return
    }

    try {
      const post = await postsApi.create({
        brand: brand.id,
        brief: input.brief,
        goals: input.goals,
        tone_hints: input.toneHints ?? [],
        target_platforms: input.platforms,
      })
      currentPost.value = post

      const { agent_run_id } = await postsApi.generate(post.id)
      currentRunId.value = agent_run_id
      openStream(agent_run_id)
    } catch (err) {
      const e = err as { response?: { data?: unknown }; message?: string }
      error.value = JSON.stringify(e.response?.data ?? e.message ?? err)
      generating.value = false
    }
  }

  async function starVariant(variantId: string) {
    const updated = await variantsApi.star(variantId)
    if (currentPost.value) {
      currentPost.value = {
        ...currentPost.value,
        variants: currentPost.value.variants.map((v) =>
          v.platform === updated.platform
            ? { ...v, is_starred: v.id === updated.id }
            : v,
        ),
      }
    }
  }

  async function unstarVariant(variantId: string) {
    const updated = await variantsApi.unstar(variantId)
    if (currentPost.value) {
      currentPost.value = {
        ...currentPost.value,
        variants: currentPost.value.variants.map((v) =>
          v.id === updated.id ? { ...v, is_starred: false } : v,
        ),
      }
    }
  }

  function _replaceVariant(updated: PostVariant) {
    if (!currentPost.value) return
    currentPost.value = {
      ...currentPost.value,
      variants: currentPost.value.variants.map((v) => (v.id === updated.id ? updated : v)),
    }
  }

  async function uploadAndAttach(variantId: string, file: File) {
    const brand = (await ensureBrand())?.id
    const asset = await mediaApi.upload(file, brand, '')
    const { variant: updated } = await variantsApi.attachImage(variantId, asset.id)
    _replaceVariant(updated)
  }

  async function generateImage(variantId: string) {
    const { variant: updated } = await variantsApi.generateImage(variantId)
    _replaceVariant(updated)
  }

  async function detachImage(variantId: string) {
    const updated = await variantsApi.detachImage(variantId)
    _replaceVariant(updated)
  }

  return {
    brands,
    activeBrandId,
    currentPost,
    currentRunId,
    events,
    generating,
    error,
    variantsByPlatform,
    totalTokens,
    loadBrands,
    runBrief,
    starVariant,
    unstarVariant,
    uploadAndAttach,
    generateImage,
    detachImage,
    refreshCurrentPost,
    closeStream,
  }
})
