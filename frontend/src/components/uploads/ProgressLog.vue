<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Progress } from 'frappe-ui'
import type { LogLine } from '@/composables/useUploader'

const props = defineProps<{
  progress: number
  log: LogLine[]
  completed: boolean
}>()

const logContainer = ref<HTMLElement | null>(null)

watch(
  () => props.log.length,
  async () => {
    await nextTick()
    if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
  },
)
</script>

<template>
  <div class="w-full max-w-lg space-y-3">
    <Progress :value="progress" />
    <div
      ref="logContainer"
      class="h-40 overflow-y-auto rounded-md border border-gray-200 bg-gray-50 p-3 font-mono text-xs sirb-scrollbar"
    >
      <div
        v-for="(line, i) in log"
        :key="i"
        class="mb-1 border-b border-gray-100 pb-1"
        :class="line.isError ? 'text-red-600' : 'text-gray-700'"
      >
        <span class="mr-2 text-gray-400">[{{ line.timestamp }}]</span>{{ line.message }}
      </div>
      <div v-if="completed" class="mt-1 font-semibold text-green-600">Upload Completed.</div>
    </div>
  </div>
</template>
