<script setup lang="ts">
import { useRouter } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { AttentionRow } from '@/composables/useAdminDashboard'

defineProps<{ rows: AttentionRow[] }>()
const router = useRouter()

function open(row: AttentionRow) {
  router.push({ name: 'project-details', params: { name: row.project_id } })
}
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-4 flex items-center gap-2">
      <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-warning">
        <FeatherIcon name="alert-triangle" class="h-4.5 w-4.5" />
      </span>
      <div>
        <h3 class="text-base font-semibold text-charcoal">Projects Needing Attention</h3>
        <p class="text-sm text-muted">
          {{ rows.length }} project{{ rows.length === 1 ? '' : 's' }} waiting more than 7 days with no update.
        </p>
      </div>
    </div>

    <EmptyState
      v-if="!rows.length"
      icon="check-circle"
      title="Nothing overdue"
      description="Every active project has moved within the last week."
    />
    <div v-else class="divide-y divide-line">
      <button
        v-for="row in rows"
        :key="row.project_id"
        class="flex w-full items-center gap-4 py-3 text-left transition-colors hover:bg-canvas"
        @click="open(row)"
      >
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium text-charcoal">{{ row.student_name }} · {{ row.project_title }}</p>
          <p class="mt-0.5 truncate text-xs text-muted">{{ row.programme }}</p>
        </div>
        <StatusBadge :status="row.status" />
        <span class="shrink-0 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-warning">
          {{ row.days_waiting }}d waiting
        </span>
        <FeatherIcon name="chevron-right" class="h-4 w-4 shrink-0 text-muted" />
      </button>
    </div>
  </div>
</template>
