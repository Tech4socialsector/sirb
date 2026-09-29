<script setup lang="ts">
defineProps<{ name?: string | null; email?: string | null }>()
</script>

<template>
  <div v-if="name" class="min-w-0">
    <p class="truncate text-sm font-medium text-charcoal" :title="email || undefined">{{ name }}</p>
    <p v-if="email" class="truncate text-xs text-muted">{{ email }}</p>
  </div>
  <span v-else class="text-muted">—</span>
</template>
