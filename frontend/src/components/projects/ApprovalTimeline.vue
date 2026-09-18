<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import type { StatusChangeEntry } from '@/types/project'

defineProps<{ history: StatusChangeEntry[] }>()
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">Approval Timeline</h3>
    <EmptyState v-if="!history.length" icon="clock" title="No status changes yet" />
    <ol v-else class="space-y-4">
      <li v-for="(entry, i) in history" :key="i" class="flex gap-3">
        <div class="flex flex-col items-center">
          <span class="h-2 w-2 shrink-0 rounded-full bg-gray-900" />
          <span v-if="i < history.length - 1" class="w-px flex-1 bg-gray-200" />
        </div>
        <div class="pb-4">
          <p class="text-sm text-gray-900">
            <span class="text-gray-500">{{ entry.from_status }}</span>
            →
            <span class="font-medium">{{ entry.to_status }}</span>
          </p>
          <p class="text-xs text-gray-500">{{ entry.changed_by }} · {{ new Date(entry.date).toLocaleString() }}</p>
        </div>
      </li>
    </ol>
  </div>
</template>
