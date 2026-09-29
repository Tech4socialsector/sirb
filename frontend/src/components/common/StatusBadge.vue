<script setup lang="ts">
import { Badge } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const theme = computed<'green' | 'orange' | 'red' | 'blue' | 'gray'>(() => {
  const s = props.status || ''
  if (s === 'Approved') return 'green'
  if (s === 'Provisionally approved') return 'blue'
  if (s.startsWith('Awaiting student correction')) return 'orange'
  if (s.startsWith('Awaiting')) return 'orange'
  return 'gray'
})
</script>

<template>
  <Badge :theme="theme" variant="subtle" size="md">{{ status }}</Badge>
</template>
