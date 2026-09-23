<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FeatherIcon, MultiSelect } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { fetchDrilldownStudents, fetchFilterOptions } from '@/services/admin'
import { fetchStatusChangeHistory } from '@/services/projects'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import { ApiError } from '@/services/api'
import type { DrilldownRow } from '@/types/admin'

const router = useRouter()
const { setContext, open: openTimelineDrawer } = useTimelineDrawer()

const rows = ref<DrilldownRow[]>([])
const loading = ref(true)
const error = ref<ApiError | null>(null)
const view = ref<'students' | 'groups'>('students')
const search = ref('')
// Academic Organizational Unit / Programme multi-select — reuses the same
// get_filter_options endpoint the Admin Console and Reports filter bars
// already call, rather than adding a new one. frappe-ui's MultiSelect
// ships its own "Clear"/"Select All" footer, so no custom UI needed there.
const programmeFilter = ref<string[]>([])
const programmeOptions = ref<{ name: string; ao_name: string }[]>([])
const programmeSelectOptions = computed(() => programmeOptions.value.map((p) => ({ label: p.ao_name, value: p.ao_name })))

async function load() {
  loading.value = true
  error.value = null
  try {
    const [drilldownRows, filterOptions] = await Promise.all([fetchDrilldownStudents({}), fetchFilterOptions()])
    rows.value = drilldownRows
    programmeOptions.value = filterOptions.programmes
  } catch (e) {
    error.value = e instanceof ApiError ? e : new ApiError('Failed to load students.', 'server')
  } finally {
    loading.value = false
  }
}

onMounted(load)

const memberCountByProject = computed(() => {
  const counts = new Map<string, number>()
  for (const r of rows.value) counts.set(r.project_id, (counts.get(r.project_id) || 0) + 1)
  return counts
})

const studentsView = computed(() =>
  rows.value.map((r) => ({
    ...r,
    project_type: (memberCountByProject.value.get(r.project_id) || 1) > 1 ? 'Group' : 'Individual',
  })),
)

const groupsView = computed(() => {
  const byProject = new Map<string, { project_id: string; project_title: string; programme: string; status: string; faculty_mentor?: string; last_updated: string; members: string[] }>()
  for (const r of rows.value) {
    if ((memberCountByProject.value.get(r.project_id) || 1) <= 1) continue
    if (!byProject.has(r.project_id)) {
      byProject.set(r.project_id, {
        project_id: r.project_id,
        project_title: r.project_title,
        programme: r.programme,
        status: r.status,
        faculty_mentor: r.faculty_mentor,
        last_updated: r.last_updated,
        members: [],
      })
    }
    byProject.get(r.project_id)!.members.push(r.student_name)
  }
  return [...byProject.values()]
})

function clearFilters() {
  search.value = ''
  programmeFilter.value = []
}

const filteredStudents = computed(() => {
  let out = studentsView.value
  if (programmeFilter.value.length) out = out.filter((r) => programmeFilter.value.includes(r.programme))
  const term = search.value.trim().toLowerCase()
  if (term) {
    out = out.filter((r) =>
      [r.student_id, r.student_name, r.project_title, r.programme, r.faculty_mentor].filter(Boolean).some((v) => v!.toLowerCase().includes(term)),
    )
  }
  return out
})

const filteredGroups = computed(() => {
  let out = groupsView.value
  if (programmeFilter.value.length) out = out.filter((g) => programmeFilter.value.includes(g.programme))
  const term = search.value.trim().toLowerCase()
  if (term) {
    out = out.filter((g) =>
      [g.project_title, g.programme, g.faculty_mentor, ...g.members].filter(Boolean).some((v) => v!.toLowerCase().includes(term)),
    )
  }
  return out
})

const individualCount = computed(() => studentsView.value.filter((r) => r.project_type === 'Individual').length)

function openProject(projectId: string) {
  router.push({ name: 'project-details', params: { name: projectId } })
}

async function viewTimeline(row: { project_id: string; project_title: string; status: string }, studentName?: string) {
  setContext({
    projectName: row.project_id,
    projectTitle: row.project_title,
    studentName: studentName || null,
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

const studentColumns: DataTableColumn[] = [
  { key: 'student_id', label: 'Student ID', sortable: true },
  { key: 'student_name', label: 'Student Name', sortable: true },
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'project_title', label: 'Project', sortable: true },
  { key: 'project_type', label: 'Type', sortable: true },
  { key: 'faculty_mentor', label: 'Mentor' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'last_updated', label: 'Updated', sortable: true },
  { key: 'actions', label: '', align: 'right' },
]

const groupColumns: DataTableColumn[] = [
  { key: 'project_title', label: 'Project', sortable: true },
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'members', label: 'Members' },
  { key: 'faculty_mentor', label: 'Mentor' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'last_updated', label: 'Updated', sortable: true },
  { key: 'actions', label: '', align: 'right' },
]
</script>

<template>
  <AppShell>
    <PageHeader title="Student &amp; Project Management" description="Every student and project group, in one place." />

    <LoadingState v-if="loading" label="Loading students…" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <template v-else>
      <div class="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total Students" :value="rows.length" icon="users" />
        <KpiCard label="Individual Projects" :value="individualCount" icon="user" tone="info" />
        <KpiCard label="Group Projects" :value="groupsView.length" icon="users" tone="info" />
        <KpiCard label="Group Members" :value="rows.length - individualCount" icon="user-plus" tone="warning" />
      </div>

      <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="inline-flex rounded-md border border-line bg-canvas p-1">
            <button
              class="rounded px-3 py-1.5 text-sm font-medium transition-colors"
              :class="view === 'students' ? 'bg-primary text-white' : 'text-muted hover:text-charcoal'"
              @click="view = 'students'"
            >
              Students
            </button>
            <button
              class="rounded px-3 py-1.5 text-sm font-medium transition-colors"
              :class="view === 'groups' ? 'bg-primary text-white' : 'text-muted hover:text-charcoal'"
              @click="view = 'groups'"
            >
              Groups
            </button>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <MultiSelect
              v-model="programmeFilter"
              :options="programmeSelectOptions"
              placeholder="All programmes"
              class="w-56"
            />
            <input
              v-model="search"
              type="text"
              placeholder="Search students, projects, mentors…"
              class="w-64 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
            />
            <button
              v-if="search || programmeFilter.length"
              class="rounded-md px-2.5 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-canvas hover:text-charcoal"
              @click="clearFilters"
            >
              Clear
            </button>
          </div>
        </div>

        <DataTable
          v-if="view === 'students'"
          :columns="studentColumns"
          :rows="filteredStudents as unknown as Record<string, unknown>[]"
          row-key="student_id"
          empty-title="No students found"
        >
          <template #cell-project_type="{ value }">
            <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="value === 'Group' ? 'bg-blue-50 text-info' : 'bg-canvas text-muted'">
              {{ value }}
            </span>
          </template>
          <template #cell-faculty_mentor="{ value }">{{ value || '—' }}</template>
          <template #cell-status="{ value }">
            <StatusBadge :status="value as string" />
          </template>
          <template #cell-last_updated="{ value }">{{ new Date(value as string).toLocaleDateString() }}</template>
          <template #cell-actions="{ row }">
            <div class="flex items-center justify-end gap-1">
              <button
                class="text-sm font-medium text-primary hover:underline"
                @click="openProject((row as unknown as DrilldownRow).project_id)"
              >
                View
              </button>
              <button
                class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-primary"
                title="View timeline"
                @click="viewTimeline(row as unknown as DrilldownRow, (row as unknown as DrilldownRow).student_name)"
              >
                <FeatherIcon name="clock" class="h-4 w-4" />
              </button>
            </div>
          </template>
        </DataTable>

        <DataTable
          v-else
          :columns="groupColumns"
          :rows="filteredGroups as unknown as Record<string, unknown>[]"
          row-key="project_id"
          empty-title="No group projects found"
          empty-description="A group project is any project with more than one student mapped to it."
        >
          <template #cell-members="{ value }">
            <div class="flex flex-wrap gap-1">
              <span v-for="name in value as string[]" :key="name" class="rounded-full bg-canvas px-2 py-0.5 text-xs text-charcoal">
                {{ name }}
              </span>
            </div>
          </template>
          <template #cell-faculty_mentor="{ value }">{{ value || '—' }}</template>
          <template #cell-status="{ value }">
            <StatusBadge :status="value as string" />
          </template>
          <template #cell-last_updated="{ value }">{{ new Date(value as string).toLocaleDateString() }}</template>
          <template #cell-actions="{ row }">
            <div class="flex items-center justify-end gap-1">
              <button
                class="text-sm font-medium text-primary hover:underline"
                @click="openProject((row as unknown as { project_id: string }).project_id)"
              >
                View Group
              </button>
              <button
                class="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-primary"
                title="View timeline"
                @click="viewTimeline(row as unknown as { project_id: string; project_title: string; status: string })"
              >
                <FeatherIcon name="clock" class="h-4 w-4" />
              </button>
            </div>
          </template>
        </DataTable>
      </div>
    </template>
  </AppShell>
</template>
