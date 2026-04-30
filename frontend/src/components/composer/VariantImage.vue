<script setup lang="ts">
import { ImagePlus, Loader2, Sparkles, Upload, X } from 'lucide-vue-next'
import { ref } from 'vue'

import type { PostVariant } from '@/api/resources'
import { useComposerStore } from '@/stores/composer'

const props = defineProps<{ variant: PostVariant }>()

const composer = useComposerStore()
const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const busy = ref<'upload' | 'generate' | 'remove' | null>(null)
const error = ref<string | null>(null)

const image = () => props.variant.media?.[0]

async function handleFile(file: File) {
  error.value = null
  busy.value = 'upload'
  try {
    await composer.uploadAndAttach(props.variant.id, file)
  } catch (e) {
    error.value = (e as Error).message ?? 'Upload failed'
  } finally {
    busy.value = null
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        await handleFile(file)
        return
      }
    }
  }
}

async function generate() {
  error.value = null
  busy.value = 'generate'
  try {
    await composer.generateImage(props.variant.id)
  } catch (e) {
    const err = e as { response?: { data?: { error?: string; message?: string } } }
    error.value =
      err.response?.data?.message ??
      err.response?.data?.error ??
      (e as Error).message ??
      'Generation failed'
  } finally {
    busy.value = null
  }
}

async function remove() {
  busy.value = 'remove'
  try {
    await composer.detachImage(props.variant.id)
  } finally {
    busy.value = null
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) handleFile(file)
}
</script>

<template>
  <div class="mt-3" tabindex="0" @paste="onPaste">
    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/webp,image/gif"
      class="hidden"
      @change="
        (e) => {
          const f = (e.target as HTMLInputElement).files?.[0]
          if (f) handleFile(f)
        }
      "
    />

    <!-- With image -->
    <div
      v-if="image()"
      class="group relative overflow-hidden rounded-md border border-border bg-muted/30"
    >
      <img
        :src="image()!.url"
        :alt="image()!.alt"
        class="block w-full max-h-72 object-contain"
        loading="lazy"
      />
      <div
        class="pointer-events-none absolute inset-x-2 top-2 flex items-center gap-1 text-[10px] uppercase tracking-wide opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100"
      >
        <span
          class="rounded bg-background/80 px-1.5 py-0.5 text-foreground backdrop-blur-sm"
        >
          {{ image()!.source === 'ai' ? '🪄 AI' : 'upload' }}
        </span>
      </div>
      <button
        class="absolute right-2 top-2 hidden rounded-full bg-background/80 p-1 text-foreground transition-colors hover:bg-destructive hover:text-destructive-foreground group-hover:block"
        :disabled="busy !== null"
        title="Remove image"
        @click="remove"
      >
        <X :size="13" />
      </button>
    </div>

    <!-- Without image: dropzone + actions -->
    <div
      v-else
      class="flex flex-col gap-2 rounded-md border border-dashed p-3 text-center transition-colors"
      :class="
        dragOver
          ? 'border-primary bg-primary/5'
          : 'border-border bg-muted/20 hover:border-muted-foreground/40'
      "
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="onDrop"
    >
      <div class="flex flex-col items-center gap-1.5 py-2">
        <ImagePlus :size="18" class="text-muted-foreground" />
        <p class="text-xs text-muted-foreground">
          Drop / paste image here, or
        </p>
        <div class="flex items-center gap-1.5">
          <button
            :disabled="busy !== null"
            class="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2 text-[11px] font-medium hover:bg-muted disabled:opacity-50"
            @click="pickFile"
          >
            <Upload v-if="busy !== 'upload'" :size="11" />
            <Loader2 v-else :size="11" class="animate-spin" />
            Upload
          </button>
          <span class="text-[11px] text-muted-foreground">or</span>
          <button
            :disabled="busy !== null"
            class="inline-flex h-7 items-center gap-1 rounded-md bg-primary/15 px-2 text-[11px] font-medium text-primary hover:bg-primary/25 disabled:opacity-50"
            @click="generate"
          >
            <Sparkles v-if="busy !== 'generate'" :size="11" />
            <Loader2 v-else :size="11" class="animate-spin" />
            Generate
          </button>
        </div>
      </div>
    </div>

    <p v-if="error" class="mt-1.5 text-[11px] text-destructive">{{ error }}</p>
  </div>
</template>
