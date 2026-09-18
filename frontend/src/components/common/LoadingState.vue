<script setup lang="ts">
import { LoadingIndicator } from 'frappe-ui'
withDefaults(defineProps<{ label?: string }>(), { label: 'Loading…' })
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 text-center text-gray-500">
    <LoadingIndicator class="h-6 w-6" />
    <p class="text-sm">{{ label }}</p>
  </div>
</template>
