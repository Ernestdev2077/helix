import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { workspacesApi, type Workspace } from '@/api/resources'

const ACTIVE_KEY = 'helix.active_workspace'

export const useWorkspaceStore = defineStore('workspace', () => {
  const workspaces = ref<Workspace[]>([])
  const activeWorkspaceId = ref<string | null>(localStorage.getItem(ACTIVE_KEY))
  const loading = ref(false)

  const activeWorkspace = computed(
    () => workspaces.value.find((w) => w.id === activeWorkspaceId.value) ?? null,
  )

  async function load() {
    loading.value = true
    try {
      workspaces.value = await workspacesApi.list()
      if (!activeWorkspaceId.value && workspaces.value.length > 0) {
        setActive(workspaces.value[0].id)
      }
    } finally {
      loading.value = false
    }
  }

  function setActive(id: string) {
    activeWorkspaceId.value = id
    localStorage.setItem(ACTIVE_KEY, id)
  }

  async function create(name: string) {
    const ws = await workspacesApi.create({ name })
    workspaces.value = [ws, ...workspaces.value]
    setActive(ws.id)
    return ws
  }

  return {
    workspaces,
    activeWorkspaceId,
    activeWorkspace,
    loading,
    load,
    setActive,
    create,
  }
})
