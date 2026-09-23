<script setup lang="ts">
import { Button, FeatherIcon } from 'frappe-ui'
import type { ApiError } from '@/services/api'

const props = defineProps<{
  error: ApiError | Error | null
}>()

defineEmits<{ retry: [] }>()

function iconFor(kind?: string) {
  switch (kind) {
    case 'permission':
      return 'lock'
    case 'not_found':
      return 'search'
    case 'network':
      return 'wifi-off'
    case 'session_expired':
      return 'log-out'
    default:
      return 'alert-triangle'
  }
}

const kind = props.error && 'kind' in props.error ? props.error.kind : undefined
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-danger/10 text-danger">
      <FeatherIcon :name="iconFor(kind)" class="h-6 w-6" />
    </div>
    <p class="max-w-sm text-sm text-muted">{{ error?.message || 'Something went wrong.' }}</p>
    <Button v-if="kind !== 'permission' && kind !== 'not_found'" variant="outline" @click="$emit('retry')">
      Try again
    </Button>
  </div>
</template>
