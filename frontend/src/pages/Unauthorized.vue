<script setup lang="ts">
import AppShell from '@/components/layout/AppShell.vue'
import EmptyState from '@/components/common/EmptyState.vue'
</script>

<template>
  <AppShell>
    <EmptyState
      icon="lock"
      title="You do not have permission to view this page"
      description="If you believe this is a mistake, contact your IRB administrator."
    />
  </AppShell>
</template>
