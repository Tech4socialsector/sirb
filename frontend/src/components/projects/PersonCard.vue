<script setup lang="ts">
import { computed } from 'vue'
import { Avatar } from 'frappe-ui'

const props = defineProps<{
  label: string
  name: string | null | undefined
  displayName?: string | null
  canEditLink: boolean
}>()

const shownName = computed(() => props.displayName || props.name)
</script>

<template>
  <div class="rounded-lg border border-line bg-paper p-5">
    <h3 class="mb-4 text-sm font-semibold text-charcoal">{{ label }}</h3>
    <div v-if="name" class="flex items-center gap-3">
      <Avatar :label="shownName || ''" size="md" />
      <p class="truncate text-sm font-medium text-charcoal">{{ shownName }}</p>
    </div>
    <p v-else class="text-sm text-muted">Not yet assigned</p>
  </div>
</template>
