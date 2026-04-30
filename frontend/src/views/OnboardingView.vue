<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next'
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-6">
    <div class="w-full max-w-lg text-center">
      <div
        class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary"
      >
        <Sparkles :size="24" />
      </div>
      <h1 class="mt-4 text-2xl font-semibold tracking-tight">Welcome to helix</h1>
      <p class="mt-2 text-sm text-muted-foreground">
        Let's set up your first workspace. This should take about 2 minutes.
      </p>
      <router-link
        to="/composer"
        class="mt-6 inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
      >
        Continue to Composer
      </router-link>
    </div>
  </div>
</template>
