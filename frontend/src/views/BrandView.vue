<script setup lang="ts">
import { Palette } from 'lucide-vue-next'
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
    <Palette :size="24" class="text-muted-foreground" />
    <h1 class="text-lg font-semibold">Brand</h1>
    <p class="max-w-md text-sm text-muted-foreground">
      Voice & tone, audience, knowledge base, connected platform accounts, posting rules.
    </p>
  </div>
</template>
