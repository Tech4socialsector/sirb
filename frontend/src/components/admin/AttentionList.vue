<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { AttentionRow } from '@/composables/useAdminDashboard'

// `clickable: false` for users who can't open project records (programme viewers).
const props = withDefaults(defineProps<{ rows: AttentionRow[]; clickable?: boolean }>(), { clickable: true })
const router = useRouter()
const search = ref('')

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.rows
  return props.rows.filter((r) =>
    [String(r.project_id), r.student_name, r.project_title, r.programme, r.status, r.faculty_mentor]
      .filter(Boolean)
      .some((v) => v!.toLowerCase().includes(term)),
  )
})

const columns: DataTableColumn[] = [
  { key: 'project_id', label: 'Project ID', sortable: true },
  { key: 'student_name', label: 'Student', sortable: true },
  { key: 'project_title', label: 'Project', sortable: true },
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'days_waiting', label: 'Waiting', align: 'right', sortable: true },
]

function open(row: Record<string, unknown>) {
  if (!props.clickable) return
  router.push({ name: 'project-details', params: { name: String(row.project_id) } })
}
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-warning">
          <FeatherIcon name="alert-triangle" class="h-4.5 w-4.5" />
        </span>
        <div>
          <h3 class="text-base font-semibold text-charcoal">Projects Needing Attention</h3>
          <p class="text-sm text-muted">
            {{ rows.length }} project{{ rows.length === 1 ? '' : 's' }} waiting more than 7 days with no update.<template v-if="clickable"> Click a row to open it.</template>
          </p>
        </div>
      </div>
      <input
        v-if="rows.length"
        v-model="search"
        type="text"
        placeholder="Search ID, student, project…"
        class="w-60 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
      />
    </div>

    <DataTable
      :columns="columns"
      :rows="filtered as unknown as Record<string, unknown>[]"
      row-key="project_id"
      :clickable-rows="clickable"
      :page-size="10"
      :empty-title="search ? 'No matching projects' : 'Nothing overdue'"
      :empty-description="search ? 'Try a different search.' : 'Every active project has moved within the last week.'"
      @row-click="open"
    >
      <template #cell-project_id="{ value }"><span class="font-semibold text-primary">#{{ value }}</span></template>
      <template #cell-student_name="{ value }"><span class="font-medium text-charcoal">{{ value }}</span></template>
      <template #cell-project_title="{ value }">
        <span class="block max-w-xs truncate" :title="(value as string) || ''">{{ value || '—' }}</span>
      </template>
      <template #cell-status="{ value }"><StatusBadge :status="value as string" /></template>
      <template #cell-days_waiting="{ value }">
        <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="(value as number) >= 30 ? 'bg-red-50 text-danger' : 'bg-amber-50 text-warning'">
          {{ value }} days
        </span>
      </template>
    </DataTable>
  </div>
</template>
