<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ name: string; subtitle: string }>()

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
})
</script>

<template>
  <div class="mb-6">
    <h1 class="text-2xl font-semibold text-charcoal">{{ greeting }}, {{ props.name }}</h1>
    <p class="mt-1 text-base text-muted">{{ props.subtitle }}</p>
  </div>
</template>
