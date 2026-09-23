<script setup lang="ts">
import { computed } from 'vue'
import type { WorklistBucket } from '@/services/projects'

const props = defineProps<{
  modelValue: WorklistBucket
  counts: Record<WorklistBucket, number>
}>()
const emit = defineEmits<{ 'update:modelValue': [WorklistBucket] }>()

const tabs: { label: string; value: WorklistBucket }[] = [
  { label: 'Pending', value: 'pending' },
  { label: 'In Progress', value: 'unapproved' },
  { label: 'Approved', value: 'approved' },
]

const active = computed(() => props.modelValue)
</script>

<template>
  <div class="flex gap-1 border-b border-line px-6">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      class="relative flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors"
      :class="active === tab.value ? 'text-charcoal' : 'text-muted hover:text-charcoal'"
      @click="emit('update:modelValue', tab.value)"
    >
      {{ tab.label }}
      <span
        class="rounded-full px-2 py-0.5 text-xs font-semibold"
        :class="active === tab.value ? 'bg-primary text-white' : 'bg-canvas text-muted'"
      >
        {{ counts[tab.value] }}
      </span>
      <span
        v-if="active === tab.value"
        class="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-primary"
      />
    </button>
  </div>
</template>
