<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || 'SIRB')
// The Home page is the root, so "Home / Home" would just repeat itself.
const isHome = computed(() => route.name === 'dashboard')
</script>

<template>
  <div>
    <h1 class="text-lg font-semibold text-charcoal">{{ title }}</h1>
    <p v-if="!isHome" class="text-xs text-muted">
      <RouterLink to="/sirb" class="hover:text-charcoal hover:underline">Home</RouterLink> / {{ title }}
    </p>
  </div>
</template>
