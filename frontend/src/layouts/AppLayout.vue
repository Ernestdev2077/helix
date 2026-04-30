<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import AppSidebar from '@/components/navigation/AppSidebar.vue'
import AppTopbar from '@/components/navigation/AppTopbar.vue'
import AgentPanel from '@/components/agent/AgentPanel.vue'
import { useWorkspaceStore } from '@/stores/workspace'

const workspaces = useWorkspaceStore()

onMounted(() => {
  if (workspaces.workspaces.length === 0) {
    void workspaces.load()
  }
})
</script>

<template>
  <div class="grid h-screen w-screen grid-cols-[56px_1fr_380px] grid-rows-[48px_1fr] bg-background">
    <AppTopbar class="col-span-3 row-start-1" />
    <AppSidebar class="col-start-1 row-start-2" />
    <main class="col-start-2 row-start-2 overflow-hidden">
      <RouterView v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <AgentPanel class="col-start-3 row-start-2" />
  </div>
</template>
