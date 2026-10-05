<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { ActivityRow } from '@/types/admin'

// `clickable: false` for users who can't open project records (programme viewers).
const props = withDefaults(defineProps<{ activity: ActivityRow[]; clickable?: boolean }>(), { clickable: true })
const router = useRouter()
const search = ref('')

// Rows can repeat the same project, so give each a stable unique key.
const rows = computed(() => props.activity.map((r, i) => ({ ...r, _key: `${r.project_id}::${r.date}::${i}`, by: actorLabel(r.performed_by) })))
const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return rows.value
  return rows.value.filter((r) =>
    [String(r.project_id), r.student_names, r.project_title, r.programme, r.from_status, r.to_status, r.by]
      .filter(Boolean)
      .some((v) => v!.toLowerCase().includes(term)),
  )
})

const columns: DataTableColumn[] = [
  { key: 'date', label: 'When', sortable: true },
  { key: 'project_id', label: 'Project ID', sortable: true },
  { key: 'student_names', label: 'Student(s)', sortable: true },
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'change', label: 'Status change' },
  { key: 'by', label: 'By', sortable: true },
]

function open(row: Record<string, unknown>) {
  if (!props.clickable) return
  router.push({ name: 'project-details', params: { name: String(row.project_id) } })
}

function relativeTime(value: string) {
  const diffMin = Math.round((Date.now() - new Date(value).getTime()) / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  if (diffDay === 1) return 'Yesterday'
  if (diffDay < 30) return `${diffDay}d ago`
  return new Date(value).toLocaleDateString(undefined, { dateStyle: 'medium' })
}
function actorLabel(email: string) {
  return !email || email === 'Administrator' ? email || '—' : email.split('@')[0].replace(/[._]/g, ' ')
}
const asRow = (r: Record<string, unknown>) => r as unknown as ActivityRow
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 class="text-base font-semibold text-charcoal">Recent Activity</h3>
        <p class="text-sm text-muted">The latest status changes across every project.<template v-if="clickable"> Click a row to open the project.</template></p>
      </div>
      <input
        v-if="activity.length"
        v-model="search"
        type="text"
        placeholder="Search ID, student, status…"
        class="w-60 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
      />
    </div>

    <DataTable
      :columns="columns"
      :rows="filtered as unknown as Record<string, unknown>[]"
      row-key="_key"
      :clickable-rows="clickable"
      :page-size="10"
      :empty-title="search ? 'No matching activity' : 'No recent status changes'"
      @row-click="open"
    >
      <template #cell-date="{ value }">
        <span class="whitespace-nowrap text-sm" :title="new Date(value as string).toLocaleString()">{{ relativeTime(value as string) }}</span>
      </template>
      <template #cell-project_id="{ value }"><span class="font-semibold text-primary">#{{ value }}</span></template>
      <template #cell-student_names="{ row }">
        <p class="max-w-[14rem] truncate font-medium text-charcoal">{{ asRow(row).student_names || '—' }}</p>
        <p v-if="asRow(row).project_title" class="max-w-[14rem] truncate text-xs text-muted">{{ asRow(row).project_title }}</p>
      </template>
      <template #cell-change="{ row }">
        <div class="flex flex-wrap items-center gap-1.5">
          <StatusBadge v-if="asRow(row).from_status" :status="asRow(row).from_status" />
          <span v-if="asRow(row).from_status" class="text-muted">→</span>
          <StatusBadge :status="asRow(row).to_status" />
        </div>
      </template>
      <template #cell-by="{ value }"><span class="whitespace-nowrap text-sm capitalize">{{ value }}</span></template>
    </DataTable>
  </div>
</template>
