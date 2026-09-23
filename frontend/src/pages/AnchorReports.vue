<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button, FeatherIcon, MultiSelect } from 'frappe-ui'
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
import PieChartCard, { type PieSlice } from '@/components/reports/PieChartCard.vue'
import DrilldownDialog from '@/components/admin/DrilldownDialog.vue'
import { useReports, BUCKET_LABELS, BUCKET_ORDER, STATUS_BUCKET, type AgingRow, type ReportFilters } from '@/composables/useReports'
import { downloadCsv, csvDateStamp } from '@/utils/csv'
import type { ProjectReportRow } from '@/types/reports'
import type { DrilldownRow } from '@/types/admin'

const filters = ref<ReportFilters>({ programmes: [], statuses: [], cycles: [], search: '' })

const {
  allRows,
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
} = useReports(filters)

onMounted(() => refresh())

const toOptions = (values: string[]) => values.map((v) => ({ label: v, value: v }))
const programmeSelectOptions = computed(() => toOptions(programmeOptions.value))
const statusSelectOptions = computed(() => toOptions(statusOptions.value))
const cycleSelectOptions = computed(() => toOptions(cycleOptions.value))

const hasActiveFilters = computed(() => {
  const f = filters.value
  return !!(f.programmes.length || f.statuses.length || f.cycles.length || f.search.trim())
})

function clearFilters() {
  filters.value = { programmes: [], statuses: [], cycles: [], search: '' }
}

const lastRefreshedLabel = computed(() =>
  lastRefreshed.value ? lastRefreshed.value.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : null,
)

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
  let rows = detailRows.value.filter((r) => (r.irb_unit || 'Unassigned') === programme)
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

// ── Pie charts ────────────────────────────────────────────────────────
// Like every other chart on this page, these read the filtered
// `detailRows`, so a slice's count always matches the drill-down it opens.
const stageSlices = computed<PieSlice[]>(() =>
  Object.keys(BUCKET_LABELS).map((k) => ({ key: k, label: BUCKET_LABELS[k], value: bucketCounts.value[k] })),
)

// Largest 7 programmes get their own slice; the rest fold into "Other" so
// the pie never needs more than the 8 fixed palette colours.
const OTHER_KEY = '__other__'
const MAX_PROGRAMME_SLICES = 7
const programmeSlices = computed<PieSlice[]>(() => {
  const counts = new Map<string, number>()
  for (const r of detailRows.value) {
    const key = r.irb_unit || 'Unassigned'
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  const top = sorted.slice(0, MAX_PROGRAMME_SLICES).map(([p, n]) => ({ key: p, label: p, value: n }))
  const rest = sorted.slice(MAX_PROGRAMME_SLICES)
  if (rest.length) top.push({ key: OTHER_KEY, label: `Other (${rest.length})`, value: rest.reduce((a, [, n]) => a + n, 0) })
  return top
})
const topProgrammes = computed(() => new Set(programmeSlices.value.filter((s) => s.key !== OTHER_KEY).map((s) => s.key)))

function openProgrammeSliceDrilldown(key: string) {
  if (key !== OTHER_KEY) return openDrilldown(key, detailRows.value.filter((r) => (r.irb_unit || 'Unassigned') === key))
  openDrilldown('Other programmes', detailRows.value.filter((r) => !topProgrammes.value.has(r.irb_unit || 'Unassigned')))
}

const AGING_KEYS = ['0-2', '3-5', '6-10', '10+'] as const
const agingSlices = computed<PieSlice[]>(() =>
  AGING_KEYS.map((k) => ({ key: k, label: `${k} days`, value: agingCounts.value[k] })),
)

type AssignmentKey = 'both' | 'primary_only' | 'secondary_only' | 'none'
const ASSIGNMENT_LABELS: Record<AssignmentKey, string> = {
  both: 'Both reviewers',
  primary_only: 'Primary only',
  secondary_only: 'Secondary only',
  none: 'Not yet assigned',
}
function assignmentOf(r: ProjectReportRow): AssignmentKey {
  if (r.primary_reviewer && r.secondary_reviewer) return 'both'
  if (r.primary_reviewer) return 'primary_only'
  if (r.secondary_reviewer) return 'secondary_only'
  return 'none'
}
const assignmentSlices = computed<PieSlice[]>(() => {
  const counts: Record<AssignmentKey, number> = { both: 0, primary_only: 0, secondary_only: 0, none: 0 }
  for (const r of detailRows.value) counts[assignmentOf(r)] += 1
  return (Object.keys(ASSIGNMENT_LABELS) as AssignmentKey[]).map((k) => ({ key: k, label: ASSIGNMENT_LABELS[k], value: counts[k] }))
})
function openAssignmentDrilldown(key: string) {
  openDrilldown(ASSIGNMENT_LABELS[key as AssignmentKey], detailRows.value.filter((r) => assignmentOf(r) === key))
}

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
  downloadCsv(
    `project-report-${csvDateStamp()}.csv`,
    ['Project ID', 'Title', 'Students', 'Programme', 'Cycle', 'Status', 'Days in Stage', 'Mentor', 'Primary Reviewer', 'Secondary Reviewer', 'Last Updated'],
    detailRows.value.map((r) => [
      r.project_name,
      r.project_title,
      r.students.map((s) => s.name).join('; '),
      r.irb_unit,
      r.irb_cycle,
      r.project_status,
      r.days_in_state,
      r.mentor_name,
      r.primary_reviewer_name,
      r.secondary_reviewer_name,
      r.last_updated,
    ]),
  )
}

// Same rows and columns as the Programme Analytics table (so it respects
// the current filters), plus a closing total row.
function exportProgrammeCsv() {
  const rows = programmeMatrix.value
  const totals = BUCKET_ORDER.map((k) => rows.reduce((a, r) => a + (r as unknown as Record<string, number>)[k], 0))
  downloadCsv(
    `programme-analytics-${csvDateStamp()}.csv`,
    ['Programme', 'Total', ...BUCKET_ORDER.map((k) => BUCKET_LABELS[k])],
    [
      ...rows.map((r) => [r.programme, r.total, ...BUCKET_ORDER.map((k) => (r as unknown as Record<string, number>)[k])]),
      ['All programmes', rows.reduce((a, r) => a + r.total, 0), ...totals],
    ],
  )
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
        <Button variant="outline" icon-left="refresh-cw" :loading="loading" @click="refresh()">
          Refresh
        </Button>
        <Button variant="outline" icon-left="download" :disabled="!detailRows.length" @click="exportDetailCsv">
          Export CSV
        </Button>
      </div>
    </div>

    <LoadingState v-if="loading && !allRows.length" label="Loading reports…" />
    <ErrorState v-else-if="error" :error="error" @retry="refresh" />
    <template v-else>
      <!-- Global filters -->
      <div class="mb-5 flex flex-wrap items-center gap-2 rounded-xl border border-line bg-paper p-4 shadow-card">
        <MultiSelect
          v-model="filters.programmes"
          :options="programmeSelectOptions"
          placeholder="All programmes"
          variant="outline"
          class="min-w-44"
        />
        <MultiSelect
          v-model="filters.statuses"
          :options="statusSelectOptions"
          placeholder="All statuses"
          variant="outline"
          class="min-w-44 max-w-80"
        />
        <MultiSelect
          v-if="cycleSelectOptions.length"
          v-model="filters.cycles"
          :options="cycleSelectOptions"
          placeholder="All cycles"
          variant="outline"
          class="min-w-36"
        />
        <div class="relative">
          <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            v-model="filters.search"
            type="text"
            placeholder="Search projects, students, reviewers…"
            class="w-72 rounded-md border border-line bg-canvas py-1.5 pl-8 pr-2 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
          />
        </div>
        <Button v-if="hasActiveFilters" variant="ghost" size="sm" icon-left="x" @click="clearFilters">
          Clear filters
        </Button>
        <span v-if="hasActiveFilters" class="ml-auto text-sm text-muted">
          Showing {{ totalProjects }} of {{ allRows.length }} projects
        </span>
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

        <!-- Pie chart overview -->
        <div class="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <PieChartCard
            title="Project Status Distribution"
            subtitle="Share of projects at each review stage."
            :slices="stageSlices"
            @select="openBucketDrilldown"
          />
          <PieChartCard
            title="Projects by Programme"
            subtitle="How projects are spread across programmes."
            :slices="programmeSlices"
            @select="openProgrammeSliceDrilldown"
          />
          <PieChartCard
            title="Project Aging"
            subtitle="Days active projects have spent in their current stage."
            :slices="agingSlices"
            @select="(k) => openAgingDrilldown(k as AgingRow['bucket'])"
          />
          <PieChartCard
            title="Reviewer Assignment"
            subtitle="Whether primary and secondary reviewers are assigned."
            :slices="assignmentSlices"
            @select="openAssignmentDrilldown"
          />
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
          <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 class="text-base font-semibold text-charcoal">Programme Analytics</h3>
              <p class="text-sm text-muted">Where each programme's projects stand right now.</p>
            </div>
            <Button variant="outline" size="sm" icon-left="download" :disabled="!programmeMatrix.length" @click="exportProgrammeCsv">
              Export CSV
            </Button>
          </div>
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
          <p class="mb-4 text-sm text-muted">{{ totalProjects }} of {{ allRows.length }} projects match the current filters.</p>
          <DataTable :columns="detailColumns" :rows="detailRows as unknown as Record<string, unknown>[]" row-key="project_name" empty-title="No matching projects">
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
