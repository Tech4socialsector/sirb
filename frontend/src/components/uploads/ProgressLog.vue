<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue'
import { FeatherIcon, Progress } from 'frappe-ui'
import type { LogLine } from '@/composables/useUploader'

const props = defineProps<{
  progress: number
  log: LogLine[]
  completed: boolean
  hadError: boolean
}>()

const logContainer = ref<HTMLElement | null>(null)

// The import runs on the "long" background queue; if nothing has been
// reported after a while, the job is most likely still waiting for a worker.
const slowStart = ref(false)
const slowStartTimer = setTimeout(() => (slowStart.value = true), 30_000)
onUnmounted(() => clearTimeout(slowStartTimer))

watch(
  () => props.log.length,
  async () => {
    await nextTick()
    if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
  },
)
</script>

<template>
  <div class="w-full max-w-3xl space-y-3">
    <Progress :value="progress" />

    <div class="overflow-hidden rounded-lg border border-line bg-paper shadow-card">
      <div ref="logContainer" class="max-h-[28rem] min-h-[12rem] space-y-2 overflow-y-auto p-4 sirb-scrollbar">
        <div v-if="!log.length" class="py-2 text-sm text-muted">
          <div class="flex items-center gap-2">
            <FeatherIcon name="loader" class="h-4 w-4 shrink-0 animate-spin" />
            Starting upload…
          </div>
          <p v-if="slowStart" class="mt-2 pl-6">
            Still waiting for the server to pick up this upload. It is queued and will start once a background
            worker is free — you can leave this page; check Error Log in Desk if nothing happens.
          </p>
        </div>
        <div
          v-for="(line, i) in log"
          :key="i"
          class="flex items-start gap-2 rounded-md px-2 py-1.5 text-sm"
          :class="line.isError ? 'bg-danger/5' : 'bg-canvas'"
        >
          <FeatherIcon
            :name="line.isError ? 'alert-circle' : 'check-circle'"
            class="mt-0.5 h-4 w-4 shrink-0"
            :class="line.isError ? 'text-danger' : 'text-success'"
          />
          <div class="min-w-0 flex-1">
            <p class="break-words" :class="line.isError ? 'text-danger' : 'text-charcoal'">{{ line.message }}</p>
            <p class="mt-0.5 text-xs text-muted">{{ line.timestamp }}</p>
          </div>
        </div>
      </div>

      <div
        v-if="completed"
        class="flex items-center gap-2 border-t border-line px-3 py-2.5 text-sm font-medium"
        :class="hadError ? 'bg-danger/5 text-danger' : 'bg-success/5 text-success'"
      >
        <FeatherIcon :name="hadError ? 'alert-triangle' : 'check-circle'" class="h-4 w-4 shrink-0" />
        {{ hadError ? 'Upload finished with errors — see above for details.' : 'Upload completed successfully.' }}
      </div>
    </div>
  </div>
</template>
