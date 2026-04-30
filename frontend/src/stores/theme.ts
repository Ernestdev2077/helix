import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export type ThemeMode = 'system' | 'dark' | 'light'

const STORAGE_KEY = 'helix.theme'
const LIGHT_MQ = '(prefers-color-scheme: light)'

function readSaved(): ThemeMode {
  if (typeof localStorage === 'undefined') return 'system'
  const v = localStorage.getItem(STORAGE_KEY)
  return v === 'dark' || v === 'light' || v === 'system' ? v : 'system'
}

function systemPrefersLight(): boolean {
  return typeof window !== 'undefined' && window.matchMedia(LIGHT_MQ).matches
}

function apply(mode: ThemeMode) {
  if (typeof document === 'undefined') return
  const useLight = mode === 'light' || (mode === 'system' && systemPrefersLight())
  document.documentElement.classList.toggle('light', useLight)
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(readSaved())

  const effective = computed<'dark' | 'light'>(() =>
    mode.value === 'system' ? (systemPrefersLight() ? 'light' : 'dark') : mode.value,
  )

  function set(next: ThemeMode) {
    mode.value = next
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, next)
    apply(next)
  }

  function toggle() {
    // Cycle: system → dark → light → system
    const next: ThemeMode =
      mode.value === 'system' ? 'dark' : mode.value === 'dark' ? 'light' : 'system'
    set(next)
  }

  // React to OS-level changes when in 'system' mode
  if (typeof window !== 'undefined') {
    const mq = window.matchMedia(LIGHT_MQ)
    mq.addEventListener('change', () => {
      if (mode.value === 'system') apply('system')
    })
  }

  // Re-apply on store init (the pre-paint script already did it, but keep
  // them in sync with the saved value):
  apply(mode.value)

  watch(mode, (v) => apply(v))

  return { mode, effective, set, toggle }
})
