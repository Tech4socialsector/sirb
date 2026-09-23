<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { fetchStatusChangeHistory } from '@/services/projects'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import type { ProjectListRow } from '@/types/project'

const props = defineProps<{
  rows: ProjectListRow[]
  emptyTitle?: string
  emptyDescription?: string
}>()

const router = useRouter()
const { setContext, open: openTimelineDrawer } = useTimelineDrawer()

function projectName(row: ProjectListRow) {
  return row.project_id || row.project_name || ''
}

function openProject(row: Record<string, unknown>) {
  const name = projectName(row as unknown as ProjectListRow)
  if (name) router.push({ name: 'project-details', params: { name } })
}

// "Edit" isn't a separate destination — the project details page already
// lets you edit any field you have permission to (see ProjectDetails.vue /
// canEdit), so a distinct Edit button would just point at the same place
// under a different label. One clear "View" action, plus Timeline since
// that's genuinely a second, different thing you can do from a row.
async function viewTimeline(row: ProjectListRow) {
  const name = projectName(row)
  if (!name) return
  setContext({
    projectName: name,
    projectTitle: row.project_title,
    studentName: row.student_name || null,
    currentStatus: row.project_status,
    history: [],
    loading: true,
  })
  openTimelineDrawer()
  try {
    const history = await fetchStatusChangeHistory(name)
    setContext({ history, loading: false })
  } catch {
    setContext({ loading: false })
  }
}

// Student worklists (Mentor/Primary/Secondary Reviewer) always carry
// student_name; a student's own "My Projects" list never does (it's
// already scoped to them) — show the column only when it's actually there.
const hasStudentColumn = computed(() => props.rows.some((r) => r.student_name))

// The worklist endpoints alias the project id as either `project_id` or
// `project_name` depending on the query — normalize to one stable key so
// DataTable always has something unique to key rows on.
const normalizedRows = computed(() => props.rows.map((r) => ({ ...r, _key: r.project_id || r.project_name })))

const columns = computed<DataTableColumn[]>(() => [
  ...(hasStudentColumn.value ? [{ key: 'student', label: 'Student', path: 'student_name', sortable: true }] : []),
  { key: 'project', label: 'Project', path: 'project_title', sortable: true },
  { key: 'cycle', label: 'Cycle', path: 'irb_cycle', sortable: true },
  { key: 'status', label: 'Status', path: 'project_status', sortable: true },
  { key: 'updated', label: 'Updated', path: 'last_updated', sortable: true },
  { key: 'actions', label: '', align: 'right' },
])
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div v-if="$slots.tabs" class="-mx-6 -mt-6 mb-5">
      <slot name="tabs" />
    </div>
    <DataTable
      :columns="columns"
      :rows="normalizedRows as unknown as Record<string, unknown>[]"
      row-key="_key"
      clickable-rows
      :empty-title="emptyTitle || 'No projects found'"
      :empty-description="emptyDescription"
      @row-click="openProject"
    >
      <template #cell-project="{ value }">
        <span class="font-medium text-charcoal">{{ value || '(Untitled)' }}</span>
      </template>
      <template #cell-cycle="{ value }">{{ value || '—' }}</template>
      <template #cell-status="{ value }">
        <StatusBadge :status="value as string" />
      </template>
      <template #cell-updated="{ value }">
        {{ value ? new Date(value as string).toLocaleDateString() : '—' }}
      </template>
      <template #cell-actions="{ row }">
        <div class="flex items-center justify-end gap-1">
          <button
            class="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-primary transition-colors hover:bg-canvas"
            @click.stop="openProject(row)"
          >
            View
          </button>
          <button
            class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-primary"
            title="View timeline"
            @click.stop="viewTimeline(row as unknown as ProjectListRow)"
          >
            <FeatherIcon name="clock" class="h-4 w-4" />
          </button>
        </div>
      </template>
    </DataTable>
  </div>
</template>
