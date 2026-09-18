<script setup lang="ts">
import AppShell from '@/components/layout/AppShell.vue'
import EmptyState from '@/components/common/EmptyState.vue'
</script>

<template>
  <AppShell>
    <EmptyState
      icon="map-pin"
      title="Page not found"
      description="The page you're looking for doesn't exist or may have moved."
    />
  </AppShell>
</template>
