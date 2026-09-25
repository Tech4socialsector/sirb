<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import type { RunStatus } from '@/types/alerts'

const props = defineProps<{ status: RunStatus }>()

const theme = computed<'green' | 'orange' | 'red' | 'blue' | 'gray'>(() => {
  switch (props.status) {
    case 'Completed':
      return 'green'
    case 'Completed with errors':
      return 'orange'
    case 'Failed':
      return 'red'
    case 'Queued':
    case 'Running':
      return 'blue'
    default:
      return 'gray'
  }
})
const label = computed(() => (props.status === 'Running' ? 'Sending…' : props.status))
</script>

<template>
  <Badge :theme="theme" variant="subtle" size="md">{{ label }}</Badge>
</template>
