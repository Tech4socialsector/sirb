<script setup lang="ts">
import { Button } from 'frappe-ui'
import type { ProjectAction } from '@/composables/useProjectActions'

defineProps<{
  actions: ProjectAction[]
  busy: boolean
}>()

const emit = defineEmits<{ action: [status: string] }>()
</script>

<template>
  <div v-if="actions.length" class="flex flex-wrap gap-2 rounded-lg border border-line bg-paper p-4">
    <Button
      v-for="action in actions"
      :key="action.targetStatus"
      :variant="action.variant === 'outline' ? 'outline' : action.variant === 'subtle' ? 'subtle' : 'solid'"
      :loading="busy"
      @click="emit('action', action.targetStatus)"
    >
      {{ action.label }}
    </Button>
  </div>
</template>
