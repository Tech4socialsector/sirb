<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || 'SIRB')
</script>

<template>
  <div>
    <h1 class="text-lg font-semibold text-charcoal">{{ title }}</h1>
    <p class="text-xs text-muted">Home / {{ title }}</p>
  </div>
</template>
