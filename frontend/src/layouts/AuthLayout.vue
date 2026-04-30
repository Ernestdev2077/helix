<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-background p-6">
    <div class="w-full max-w-md">
      <div class="mb-8 text-center">
        <h1 class="text-2xl font-semibold tracking-tight">🧬 helix</h1>
        <p class="mt-2 text-sm text-muted-foreground">agent-native SMM workspace</p>
      </div>
      <RouterView />
    </div>
  </div>
</template>
