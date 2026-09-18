<script setup lang="ts">
import { Avatar } from 'frappe-ui'

defineProps<{
  label: string
  name: string | null | undefined
  canEditLink: boolean
}>()
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">{{ label }}</h3>
    <div v-if="name" class="flex items-center gap-3">
      <Avatar :label="name" size="md" />
      <p class="truncate text-sm font-medium text-gray-900">{{ name }}</p>
    </div>
    <p v-else class="text-sm text-gray-400">Not yet assigned</p>
  </div>
</template>
