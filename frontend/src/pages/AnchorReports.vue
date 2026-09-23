<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import PersonCell from '@/components/common/PersonCell.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import PipelineFlow, { type PipelineStage } from '@/components/dashboard/PipelineFlow.vue'
import BucketBarChart from '@/components/reports/BucketBarChart.vue'
import DrilldownDialog from '@/components/admin/DrilldownDialog.vue'
import { useReports, BUCKET_LABELS, STATUS_BUCKET, type AgingRow } from '@/composables/useReports'
import type { ProjectReportRow } from '@/types/reports'
import type { DrilldownRow } from '@/types/admin'

const {
  detailRows,
  loading,
  error,
  lastRefreshed,
  refresh,
  programmeOptions,
  statusOptions,
  cycleOptions,
  bucketCounts,
  totalProjects,
  programmeMatrix,
  agingRows,
  agingCounts,
  mentorWorkload,
  primaryReviewerWorkload,
  secondaryReviewerWorkload,
} = useReports()

const programmeFilter = ref('')
const statusFilter = ref('')
const cycleFilter = ref('')
const search = ref('')

onMounted(() => refresh())

// Programme is the one filter the underlying report API actually accepts
// as a parameter, so changing it re-runs the report server-side rather
// than just re-filtering what's already loaded.
async function onProgrammeChange() {
  await refresh(programmeFilter.value || undefined)
}

function clearFilters() {
  programmeFilter.value = ''
  statusFilter.value = ''
  cycleFilter.value = ''
  search.value = ''
  refresh()
}

const lastRefreshedLabel = computed(() =>
  lastRefreshed.value ? lastRefreshed.value.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : null,
)

// Status + cycle + search filter the already-fetched rows client-side —
// no extra request, since the one report call already returned everything.
const filteredDetailRows = computed(() => {
  let rows = detailRows.value
  if (statusFilter.value) rows = rows.filter((r) => r.project_status === statusFilter.value)
  if (cycleFilter.value) rows = rows.filter((r) => r.irb_cycle === cycleFilter.value)
  const term = search.value.trim().toLowerCase()
  if (term) {
    rows = rows.filter((r) =>
      [r.project_title, r.irb_unit, r.mentor_name, r.primary_reviewer_name, r.secondary_reviewer_name, ...r.students.map((s) => s.name)]
        .filter(Boolean)
        .some((v) => v!.toLowerCase().includes(term)),
    )
  }
  return rows
})

function toDrilldownRows(rows: ProjectReportRow[]): DrilldownRow[] {
  return rows.map((r) => ({
    student_id: r.students[0]?.email || String(r.project_name),
    student_name: r.students.map((s) => s.name).join(', ') || '—',
    programme: r.irb_unit,
    project_id: String(r.project_name),
    project_title: r.project_title,
    status: r.project_status,
    faculty_mentor: r.mentor_name || undefined,
    primary_reviewer: r.primary_reviewer_name || undefined,
    secondary_reviewer: r.secondary_reviewer_name || undefined,
    last_updated: r.last_updated,
  }))
}

const drilldownOpen = ref(false)
const drilldownTitle = ref('')
const drilldownRows = ref<DrilldownRow[]>([])

function openDrilldown(title: string, rows: ProjectReportRow[]) {
  drilldownTitle.value = title
  drilldownRows.value = toDrilldownRows(rows)
  drilldownOpen.value = true
}

function openBucketDrilldown(bucketKey: string) {
  const rows = detailRows.value.filter((r) => STATUS_BUCKET[r.project_status] === bucketKey)
  openDrilldown(BUCKET_LABELS[bucketKey], rows)
}

function openAgingDrilldown(bucket: AgingRow['bucket']) {
  const rows = agingRows.value.filter((r) => r.bucket === bucket)
  openDrilldown(`${bucket} days waiting`, rows)
}

function openProgrammeDrilldown(programme: string, bucketKey?: string) {
  let rows = detailRows.value.filter((r) => r.irb_unit === programme)
  if (bucketKey) rows = rows.filter((r) => STATUS_BUCKET[r.project_status] === bucketKey)
  openDrilldown(bucketKey ? `${programme} — ${BUCKET_LABELS[bucketKey]}` : programme, rows)
}

function openPersonDrilldown(role: 'mentor' | 'primary_reviewer' | 'secondary_reviewer', name: string, kind: 'pending' | 'completed' | 'returned') {
  const field = role === 'mentor' ? 'mentor_name' : role === 'primary_reviewer' ? 'primary_reviewer_name' : 'secondary_reviewer_name'
  const bucketKey = role === 'mentor' ? 'mentor_review' : role === 'primary_reviewer' ? 'primary_review' : 'secondary_review'
  let rows = detailRows.value.filter((r) => r[field] === name)
  if (kind === 'pending') rows = rows.filter((r) => STATUS_BUCKET[r.project_status] === bucketKey)
  else if (kind === 'completed') rows = rows.filter((r) => r.project_status === 'Approved')
  else rows = rows.filter((r) => r.project_status.includes('correction'))
  openDrilldown(`${name} — ${kind}`, rows)
}

const pipelineStages = computed<PipelineStage[]>(() => [
  { key: 'student_action', label: 'Student', count: bucketCounts.value.student_action, icon: 'user' },
  { key: 'mentor_review', label: 'Mentor', count: bucketCounts.value.mentor_review, icon: 'user-check' },
  { key: 'primary_review', label: 'Primary Review', count: bucketCounts.value.primary_review, icon: 'eye' },
  { key: 'secondary_review', label: 'Secondary Review', count: bucketCounts.value.secondary_review, icon: 'eye' },
  { key: 'final_approval', label: 'Final Approval', count: bucketCounts.value.final_approval, icon: 'flag' },
  { key: 'approved', label: 'Approved', count: bucketCounts.value.approved, icon: 'check-circle' },
])

const detailColumns: DataTableColumn[] = [
  { key: 'project_id', label: 'Project ID', path: 'project_name', sortable: true },
  { key: 'title', label: 'Project Title', path: 'project_title', sortable: true },
  { key: 'students', label: 'Student(s)' },
  { key: 'programme', label: 'Programme', path: 'irb_unit', sortable: true },
  { key: 'cycle', label: 'Cycle', path: 'irb_cycle', sortable: true },
  { key: 'status', label: 'Status', path: 'project_status', sortable: true },
  { key: 'days', label: 'Days in Stage', path: 'days_in_state', align: 'right', sortable: true },
  { key: 'mentor', label: 'Mentor' },
  { key: 'primary', label: 'Primary Reviewer' },
  { key: 'secondary', label: 'Secondary Reviewer' },
  { key: 'updated', label: 'Last Updated', path: 'last_updated', sortable: true },
  { key: 'actions', label: '', align: 'right' },
]

function exportDetailCsv() {
  const header = ['Project ID', 'Title', 'Students', 'Programme', 'Cycle', 'Status', 'Days in Stage', 'Mentor', 'Primary Reviewer', 'Secondary Reviewer', 'Last Updated']
  const lines = [header.join(',')]
  for (const r of filteredDetailRows.value) {
    lines.push(
      [r.project_name, r.project_title, r.students.map((s) => s.name).join('; '), r.irb_unit, r.irb_cycle || '', r.project_status, r.days_in_state, r.mentor_name || '', r.primary_reviewer_name || '', r.secondary_reviewer_name || '', r.last_updated]
        .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`)
        .join(','),
    )
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'project-report.csv'
  a.click()
  URL.revokeObjectURL(url)
}

const workloadTab = ref<'mentor' | 'primary_reviewer' | 'secondary_reviewer'>('mentor')
const workloadRows = computed(() => {
  if (workloadTab.value === 'mentor') return mentorWorkload.value
  if (workloadTab.value === 'primary_reviewer') return primaryReviewerWorkload.value
  return secondaryReviewerWorkload.value
})
const workloadColumns: DataTableColumn[] = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'assigned', label: 'Assigned', align: 'right', sortable: true },
  { key: 'pending', label: 'Pending', align: 'right', sortable: true },
  { key: 'completed', label: 'Completed', align: 'right', sortable: true },
  { key: 'returned', label: 'Returned', align: 'right', sortable: true },
]
</script>

<template>
  <AppShell>
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-charcoal">Project Reports</h1>
        <p class="mt-1 text-base text-muted">Explore project progress, review workload and programme performance.</p>
        <p v-if="lastRefreshedLabel" class="mt-1 text-xs text-muted">Last refreshed: {{ lastRefreshedLabel }}</p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <Button variant="outline" icon-left="refresh-cw" :loading="loading" @click="refresh(programmeFilter || undefined)">
          Refresh
        </Button>
        <Button variant="outline" icon-left="download" :disabled="!filteredDetailRows.length" @click="exportDetailCsv">
          Export CSV
        </Button>
      </div>
    </div>

    <LoadingState v-if="loading && !detailRows.length" label="Loading reports…" />
    <ErrorState v-else-if="error" :error="error" @retry="() => refresh(programmeFilter || undefined)" />
    <template v-else>
      <!-- Global filters -->
      <div class="mb-5 flex flex-wrap items-center gap-2 rounded-xl border border-line bg-paper p-4 shadow-card">
        <select
          v-model="programmeFilter"
          class="rounded-md border border-line bg-canvas px-2.5 py-1.5 text-sm text-charcoal focus:border-primary focus:outline-none"
          @change="onProgrammeChange"
        >
          <option value="">All programmes</option>
          <option v-for="p in programmeOptions" :key="p" :value="p">{{ p }}</option>
        </select>
        <select
          v-model="statusFilter"
          class="rounded-md border border-line bg-canvas px-2.5 py-1.5 text-sm text-charcoal focus:border-primary focus:outline-none"
        >
          <option value="">All statuses</option>
          <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
        </select>
        <select
          v-if="cycleOptions.length"
          v-model="cycleFilter"
          class="rounded-md border border-line bg-canvas px-2.5 py-1.5 text-sm text-charcoal focus:border-primary focus:outline-none"
        >
          <option value="">All cycles</option>
          <option v-for="c in cycleOptions" :key="c" :value="c">{{ c }}</option>
        </select>
        <div class="relative">
          <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            v-model="search"
            type="text"
            placeholder="Search projects, students, reviewers…"
            class="w-64 rounded-md border border-line bg-canvas py-1.5 pl-8 pr-2 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
          />
        </div>
        <Button
          v-if="programmeFilter || statusFilter || cycleFilter || search"
          variant="ghost"
          size="sm"
          @click="clearFilters"
        >
          Clear
        </Button>
      </div>

      <EmptyState
        v-if="!totalProjects"
        icon="inbox"
        title="No projects found"
        description="No projects match the selected report filters."
      />
      <template v-else>
        <!-- KPI summary -->
        <div class="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Total Projects" :value="totalProjects" icon="folder" clickable @click="openDrilldown('All Projects', detailRows)" />
          <KpiCard
            label="In Review"
            :value="bucketCounts.primary_review + bucketCounts.secondary_review"
            icon="eye"
            tone="info"
            support="Primary + secondary review"
            clickable
            @click="openDrilldown('In Review', detailRows.filter((r) => ['primary_review', 'secondary_review'].includes(STATUS_BUCKET[r.project_status])))"
          />
          <KpiCard label="Approved" :value="bucketCounts.approved" icon="check-circle" tone="success" clickable @click="openBucketDrilldown('approved')" />
          <KpiCard
            label="Returned for Correction"
            :value="detailRows.filter((r) => r.project_status.includes('correction')).length"
            icon="corner-up-left"
            tone="warning"
            clickable
            @click="openDrilldown('Returned for Correction', detailRows.filter((r) => r.project_status.includes('correction')))"
          />
        </div>

        <!-- Workflow pipeline -->
        <div class="mb-5">
          <PipelineFlow :stages="pipelineStages" @select="openBucketDrilldown" />
        </div>

        <!-- Status distribution -->
        <div class="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
            <h3 class="text-base font-semibold text-charcoal">Workflow Stage Distribution</h3>
            <p class="mb-2 text-sm text-muted">Click a stage to see its projects.</p>
            <BucketBarChart
              :labels="Object.keys(BUCKET_LABELS).map((k) => BUCKET_LABELS[k])"
              :values="Object.keys(BUCKET_LABELS).map((k) => bucketCounts[k])"
              @select="(i) => openBucketDrilldown(Object.keys(BUCKET_LABELS)[i])"
            />
          </div>
          <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
            <h3 class="mb-4 text-base font-semibold text-charcoal">Status Summary</h3>
            <DataTable
              :columns="[
                { key: 'label', label: 'Stage' },
                { key: 'count', label: 'Count', align: 'right', sortable: true },
                { key: 'pct', label: 'Share', align: 'right' },
                { key: 'action', label: '', align: 'right' },
              ]"
              :rows="
                Object.keys(BUCKET_LABELS).map((k) => ({
                  key: k,
                  label: BUCKET_LABELS[k],
                  count: bucketCounts[k],
                  pct: totalProjects ? Math.round((bucketCounts[k] / totalProjects) * 100) + '%' : '0%',
                }))
              "
              row-key="key"
              :page-size="10"
            >
              <template #cell-action="{ row }">
                <button class="text-sm font-medium text-primary hover:underline" @click="openBucketDrilldown((row as unknown as { key: string }).key)">
                  View
                </button>
              </template>
            </DataTable>
          </div>
        </div>

        <!-- Programme analytics -->
        <div class="mb-5 rounded-xl border border-line bg-paper p-6 shadow-card">
          <h3 class="text-base font-semibold text-charcoal">Programme Analytics</h3>
          <p class="mb-4 text-sm text-muted">Where each programme's projects stand right now.</p>
          <BucketBarChart
            :labels="programmeMatrix.map((r) => r.programme)"
            :values="programmeMatrix.map((r) => r.total)"
            @select="(i) => openProgrammeDrilldown(programmeMatrix[i].programme)"
          />
          <div class="mt-4">
            <DataTable
              :columns="[
                { key: 'programme', label: 'Programme', sortable: true },
                { key: 'total', label: 'Total', align: 'right', sortable: true },
                { key: 'student_action', label: 'Student', align: 'right', sortable: true },
                { key: 'mentor_review', label: 'Mentor', align: 'right', sortable: true },
                { key: 'primary_review', label: 'Primary', align: 'right', sortable: true },
                { key: 'secondary_review', label: 'Secondary', align: 'right', sortable: true },
                { key: 'final_approval', label: 'Final', align: 'right', sortable: true },
                { key: 'approved', label: 'Approved', align: 'right', sortable: true },
              ]"
              :rows="programmeMatrix as unknown as Record<string, unknown>[]"
              row-key="programme"
            >
              <template #cell-total="{ row, value }">
                <button class="font-semibold text-primary hover:underline" @click="openProgrammeDrilldown((row as unknown as { programme: string }).programme)">
                  {{ value }}
                </button>
              </template>
              <template v-for="bk in ['student_action', 'mentor_review', 'primary_review', 'secondary_review', 'final_approval', 'approved']" :key="bk" #[`cell-${bk}`]="{ row, value }">
                <button
                  v-if="(value as number) > 0"
                  class="hover:underline"
                  @click="openProgrammeDrilldown((row as unknown as { programme: string }).programme, bk)"
                >
                  {{ value }}
                </button>
                <span v-else class="text-muted">0</span>
              </template>
            </DataTable>
          </div>
        </div>

        <!-- Review workload -->
        <div class="mb-5 rounded-xl border border-line bg-paper p-6 shadow-card">
          <h3 class="mb-4 text-base font-semibold text-charcoal">Mentor &amp; Reviewer Workload</h3>
          <div class="mb-4 inline-flex rounded-md border border-line bg-canvas p-1">
            <button
              v-for="tab in [{ key: 'mentor', label: 'Mentors' }, { key: 'primary_reviewer', label: 'Primary Reviewers' }, { key: 'secondary_reviewer', label: 'Secondary Reviewers' }]"
              :key="tab.key"
              class="rounded px-3 py-1.5 text-sm font-medium transition-colors"
              :class="workloadTab === tab.key ? 'bg-primary text-white' : 'text-muted hover:text-charcoal'"
              @click="workloadTab = tab.key as typeof workloadTab"
            >
              {{ tab.label }}
            </button>
          </div>
          <DataTable
            :columns="workloadColumns"
            :rows="workloadRows as unknown as Record<string, unknown>[]"
            row-key="name"
            empty-title="No workload data"
            :empty-description="`No ${workloadTab === 'mentor' ? 'mentors' : 'reviewers'} have active projects yet.`"
          >
            <template #cell-pending="{ row, value }">
              <button v-if="(value as number) > 0" class="font-medium text-warning hover:underline" @click="openPersonDrilldown(workloadTab, (row as unknown as { name: string }).name, 'pending')">
                {{ value }}
              </button>
              <span v-else class="text-muted">0</span>
            </template>
            <template #cell-completed="{ row, value }">
              <button v-if="(value as number) > 0" class="font-medium text-success hover:underline" @click="openPersonDrilldown(workloadTab, (row as unknown as { name: string }).name, 'completed')">
                {{ value }}
              </button>
              <span v-else class="text-muted">0</span>
            </template>
            <template #cell-returned="{ row, value }">
              <button v-if="(value as number) > 0" class="hover:underline" @click="openPersonDrilldown(workloadTab, (row as unknown as { name: string }).name, 'returned')">
                {{ value }}
              </button>
              <span v-else class="text-muted">0</span>
            </template>
          </DataTable>
        </div>

        <!-- Project aging -->
        <div class="mb-5 rounded-xl border border-line bg-paper p-6 shadow-card">
          <h3 class="text-base font-semibold text-charcoal">Project Aging</h3>
          <p class="mb-4 text-sm text-muted">How long active projects have sat in their current stage.</p>
          <BucketBarChart
            :labels="['0-2 days', '3-5 days', '6-10 days', '10+ days']"
            :values="[agingCounts['0-2'], agingCounts['3-5'], agingCounts['6-10'], agingCounts['10+']]"
            @select="(i) => openAgingDrilldown((['0-2', '3-5', '6-10', '10+'] as const)[i])"
          />
        </div>

        <!-- Detailed project report -->
        <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
          <h3 class="mb-1 text-base font-semibold text-charcoal">Detailed Project Report</h3>
          <p class="mb-4 text-sm text-muted">{{ filteredDetailRows.length }} of {{ totalProjects }} projects match the current filters.</p>
          <DataTable :columns="detailColumns" :rows="filteredDetailRows as unknown as Record<string, unknown>[]" row-key="project_name" empty-title="No matching projects">
            <template #cell-title="{ value }">
              <span class="line-clamp-2 max-w-xs">{{ value }}</span>
            </template>
            <template #cell-students="{ row }">
              <div class="space-y-1">
                <PersonCell v-for="s in (row as unknown as ProjectReportRow).students" :key="s.email" :name="s.name" :email="s.email" />
              </div>
            </template>
            <template #cell-status="{ value }">
              <StatusBadge :status="value as string" />
            </template>
            <template #cell-mentor="{ row }">
              <PersonCell :name="(row as unknown as ProjectReportRow).mentor_name" :email="(row as unknown as ProjectReportRow).mentor_email" />
            </template>
            <template #cell-primary="{ row }">
              <PersonCell :name="(row as unknown as ProjectReportRow).primary_reviewer_name" :email="(row as unknown as ProjectReportRow).primary_reviewer_email" />
            </template>
            <template #cell-secondary="{ row }">
              <PersonCell :name="(row as unknown as ProjectReportRow).secondary_reviewer_name" :email="(row as unknown as ProjectReportRow).secondary_reviewer_email" />
            </template>
            <template #cell-updated="{ value }">
              {{ new Date(value as string).toLocaleDateString() }}
            </template>
            <template #cell-actions="{ row }">
              <RouterLink
                :to="`/sirb/projects/${(row as unknown as ProjectReportRow).project_name}`"
                class="text-sm font-medium text-primary hover:underline"
              >
                View
              </RouterLink>
            </template>
          </DataTable>
        </div>
      </template>

      <DrilldownDialog v-model="drilldownOpen" :title="drilldownTitle" :rows="drilldownRows" />
    </template>
  </AppShell>
</template>
