<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, FeatherIcon } from 'frappe-ui'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { fetchStatusChangeHistory } from '@/services/projects'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import { useRoles } from '@/composables/useRoles'
import type { DrilldownRow } from '@/types/admin'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    description?: string
    rows: DrilldownRow[]
    loading?: boolean
    /** Route to send "Open Projects" to — a worklist already scoped to
     * this drill-down's context, e.g. /sirb/review/primary. Omit to hide
     * the button rather than link somewhere generic. */
    openProjectsTo?: string
  }>(),
  { loading: false },
)
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const router = useRouter()
const { setContext, open: openTimelineDrawer } = useTimelineDrawer()

const search = ref('')
const statusFilter = ref('')
const programmeFilter = ref('')

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      search.value = ''
      statusFilter.value = ''
      programmeFilter.value = ''
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  },
)

const statusOptions = computed(() => [...new Set(props.rows.map((r) => r.status))].sort())
const programmeOptions = computed(() => [...new Set(props.rows.map((r) => r.programme).filter(Boolean))].sort())

// Every filter here runs against the single already-fetched row set — no
// extra network call per keystroke/dropdown change.
const filteredRows = computed(() => {
  let out = props.rows
  if (statusFilter.value) out = out.filter((r) => r.status === statusFilter.value)
  if (programmeFilter.value) out = out.filter((r) => r.programme === programmeFilter.value)
  const term = search.value.trim().toLowerCase()
  if (term) {
    out = out.filter((r) =>
      [r.student_name, r.project_title, r.programme, r.faculty_mentor, r.primary_reviewer, r.secondary_reviewer]
        .filter(Boolean)
        .some((v) => v!.toLowerCase().includes(term)),
    )
  }
  return out
})

function clearFilters() {
  search.value = ''
  statusFilter.value = ''
  programmeFilter.value = ''
}

// Project details and timelines are only readable with an IRB Project
// role (and then only for projects the user is on — sirb/permissions.py).
// Anchor-only users see the report rows but have nothing to open, so the
// View / timeline actions would only ever fail for them.
const { hasRole } = useRoles()
const canOpenProjects = computed(() =>
  hasRole('System Manager', 'Administrator', 'Student', 'Faculty Mentor', 'Primary IRB Reviewer', 'Secondary IRB Reviewer'),
)

const allColumns: DataTableColumn[] = [
  { key: 'student', label: 'Student', path: 'student_name', sortable: true },
  { key: 'project', label: 'Project', path: 'project_title', sortable: true },
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'mentor', label: 'Mentor', path: 'faculty_mentor' },
  { key: 'updated', label: 'Last Updated', path: 'last_updated', sortable: true },
  { key: 'actions', label: '', align: 'right' },
]
const columns = computed(() => (canOpenProjects.value ? allColumns : allColumns.filter((c) => c.key !== 'actions')))

function close() {
  emit('update:modelValue', false)
}

function viewProject(row: DrilldownRow) {
  close()
  router.push({ name: 'project-details', params: { name: row.project_id } })
}

async function viewTimeline(row: DrilldownRow) {
  setContext({
    projectName: row.project_id,
    projectTitle: row.project_title,
    studentName: row.student_name,
    currentStatus: row.status,
    history: [],
    loading: true,
  })
  openTimelineDrawer()
  try {
    const history = await fetchStatusChangeHistory(row.project_id)
    setContext({ history, loading: false })
  } catch {
    setContext({ loading: false })
  }
}

function openProjects() {
  if (props.openProjectsTo) router.push(props.openProjectsTo)
}

function exportCsv() {
  const header = [
    'Student Name',
    'Student ID',
    'Programme',
    'Status',
    'Faculty Mentor',
    'Primary Reviewer',
    'Secondary Reviewer',
    'Last Updated',
  ]
  const lines = [header.join(',')]
  for (const r of filteredRows.value) {
    lines.push(
      [
        r.student_name,
        r.student_id,
        r.programme,
        r.status,
        r.faculty_mentor || '',
        r.primary_reviewer || '',
        r.secondary_reviewer || '',
        r.last_updated,
      ]
        .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`)
        .join(','),
    )
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.title.replace(/[\\/:*?"<>|]/g, '-')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-100"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div v-if="modelValue" class="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-charcoal/40" @click="close" />
        <div
          class="relative flex h-[88vh] max-h-[88vh] w-[92vw] max-w-[1400px] flex-col overflow-hidden rounded-xl bg-paper shadow-xl sm:w-[90vw]"
        >
          <!-- Sticky header -->
          <header class="flex shrink-0 items-start justify-between gap-3 border-b border-line px-6 py-4">
            <div class="min-w-0">
              <h2 class="text-lg font-semibold text-charcoal">{{ title }} ({{ rows.length }})</h2>
              <p class="mt-0.5 text-sm text-muted">{{ description || 'Matching project records' }}</p>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <Button v-if="filteredRows.length" variant="outline" size="sm" icon-left="download" @click="exportCsv">
                Export CSV
              </Button>
              <Button v-if="openProjectsTo" variant="outline" size="sm" @click="openProjects">Open Projects</Button>
              <button
                class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-charcoal"
                aria-label="Close"
                @click="close"
              >
                <FeatherIcon name="x" class="h-5 w-5" />
              </button>
            </div>
          </header>

          <!-- Sticky filter bar -->
          <div class="flex shrink-0 flex-wrap items-center gap-2 border-b border-line px-6 py-3">
            <div class="relative">
              <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                v-model="search"
                type="text"
                placeholder="Search students, projects, mentors…"
                class="w-64 rounded-md border border-line bg-canvas py-1.5 pl-8 pr-2 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
              />
            </div>
            <select
              v-model="statusFilter"
              class="rounded-md border border-line bg-canvas px-2.5 py-1.5 text-sm text-charcoal focus:border-primary focus:outline-none"
            >
              <option value="">All statuses</option>
              <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
            </select>
            <select
              v-model="programmeFilter"
              class="rounded-md border border-line bg-canvas px-2.5 py-1.5 text-sm text-charcoal focus:border-primary focus:outline-none"
            >
              <option value="">All programmes</option>
              <option v-for="p in programmeOptions" :key="p" :value="p">{{ p }}</option>
            </select>
            <Button
              v-if="search || statusFilter || programmeFilter"
              variant="ghost"
              size="sm"
              @click="clearFilters"
            >
              Clear filters
            </Button>
          </div>

          <!-- Scrolling table body -->
          <div class="flex-1 overflow-y-auto sirb-scrollbar px-6 py-4">
            <DataTable
              :columns="columns"
              :rows="filteredRows as unknown as Record<string, unknown>[]"
              row-key="project_id"
              :loading="loading"
              empty-title="No matching projects"
              empty-description="Try a different search term or clear the filters."
              :page-size="10"
            >
              <template #cell-status="{ value }">
                <StatusBadge :status="value as string" />
              </template>
              <template #cell-updated="{ value }">
                {{ new Date(value as string).toLocaleDateString() }}
              </template>
              <template #cell-actions="{ row }">
                <div class="flex items-center justify-end gap-1">
                  <button
                    class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-primary"
                    title="View project"
                    @click.stop="viewProject(row as unknown as DrilldownRow)"
                  >
                    <FeatherIcon name="external-link" class="h-4 w-4" />
                  </button>
                  <button
                    class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-primary"
                    title="View timeline"
                    @click.stop="viewTimeline(row as unknown as DrilldownRow)"
                  >
                    <FeatherIcon name="clock" class="h-4 w-4" />
                  </button>
                </div>
              </template>
            </DataTable>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
