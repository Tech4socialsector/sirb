<script setup lang="ts">
withDefaults(defineProps<{ title: string; description?: string }>(), {})
</script>

<template>
  <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
    <div>
      <h1 class="text-xl font-semibold text-charcoal">{{ title }}</h1>
      <p v-if="description" class="mt-0.5 text-sm text-muted">{{ description }}</p>
    </div>
    <div class="flex items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
