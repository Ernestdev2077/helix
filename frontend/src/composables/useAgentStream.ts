import { onUnmounted, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

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

/**
 * Subscribes to a single AgentRun's event stream over WebSocket.
 *
 * Merges replay (stored events fetched on connect) with the live pub/sub
 * stream, deduplicates by sequence, and exposes a flat, ordered array.
 */
export function useAgentStream() {
  const events = ref<AgentEvent[]>([])
  const connected = ref(false)
  const error = ref<string | null>(null)

  let socket: WebSocket | null = null

  function open(runId: string) {
    close()

    const auth = useAuthStore()
    const wsBase =
      import.meta.env.VITE_WS_URL ||
      (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

    const url = `${wsBase}/ws/agent-runs/${runId}/`
    socket = new WebSocket(url)

    socket.onopen = () => {
      connected.value = true
      error.value = null
      if (auth.accessToken) {
        socket?.send(JSON.stringify({ type: 'auth', token: auth.accessToken }))
      }
    }

    socket.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as AgentEvent & { type?: string }
        const existing = events.value.find((e) => e.sequence === payload.sequence)
        if (existing) return
        events.value = [...events.value, payload].sort((a, b) => a.sequence - b.sequence)
      } catch {
        // ignore malformed frames
      }
    }

    socket.onerror = () => {
      error.value = 'stream_error'
    }

    socket.onclose = () => {
      connected.value = false
    }
  }

  function close() {
    socket?.close()
    socket = null
    connected.value = false
    events.value = []
  }

  onUnmounted(close)

  return { events, connected, error, open, close }
}
