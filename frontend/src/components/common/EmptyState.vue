<script setup lang="ts">
import { FeatherIcon } from 'frappe-ui'

withDefaults(
  defineProps<{
    title: string
    description?: string
    icon?: string
  }>(),
  { icon: 'inbox' },
)
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 py-16 text-center">
    <div class="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-canvas text-muted">
      <FeatherIcon :name="icon" class="h-6 w-6" />
    </div>
    <p class="text-base font-medium text-charcoal">{{ title }}</p>
    <p v-if="description" class="max-w-sm text-sm text-muted">{{ description }}</p>
  </div>
</template>
