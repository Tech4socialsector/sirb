<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useRoles } from '@/composables/useRoles'

const route = useRoute()
const title = computed(() => (route.meta.title as string) || 'SIRB')
// The Home page is the root, so "Home / Home" would just repeat itself.
const isHome = computed(() => route.name === 'dashboard')
// Console-only users have no Home page (it redirects to the console).
const { isConsoleOnly } = useRoles()
</script>

<template>
  <div>
    <h1 class="text-lg font-semibold text-charcoal">{{ title }}</h1>
    <p v-if="!isHome && !isConsoleOnly" class="text-xs text-muted">
      <RouterLink to="/sirb" class="hover:text-charcoal hover:underline">Home</RouterLink> / {{ title }}
    </p>
  </div>
</template>
