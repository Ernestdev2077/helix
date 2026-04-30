<script setup lang="ts">
import { Calendar } from 'lucide-vue-next'
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
    <Calendar :size="24" class="text-muted-foreground" />
    <h1 class="text-lg font-semibold">Calendar</h1>
    <p class="max-w-md text-sm text-muted-foreground">
      Month / Week / List views, drag-and-drop reschedule, "best time to post" suggestions based
      on historical metrics. Coming in Phase 2.
    </p>
  </div>
</template>
