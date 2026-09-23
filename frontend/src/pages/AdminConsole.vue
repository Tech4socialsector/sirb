<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DashboardGreeting from '@/components/dashboard/DashboardGreeting.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import PipelineFlow, { type PipelineStage } from '@/components/dashboard/PipelineFlow.vue'
import TrendChart from '@/components/dashboard/TrendChart.vue'
import WorkflowChart from '@/components/dashboard/WorkflowChart.vue'
import FilterBar from '@/components/admin/FilterBar.vue'
import AttentionList from '@/components/admin/AttentionList.vue'
import ProgrammeAnalyticsTable from '@/components/admin/ProgrammeAnalyticsTable.vue'
import RoleWorkloadPanel from '@/components/admin/RoleWorkloadPanel.vue'
import ActivityFeed from '@/components/admin/ActivityFeed.vue'
import DrilldownDialog from '@/components/admin/DrilldownDialog.vue'
import { useAuth } from '@/composables/useAuth'
import { useAdminDashboard } from '@/composables/useAdminDashboard'
import { fetchRecordCounts, type ManagedDoctype } from '@/services/records'
import { ApiError } from '@/services/api'
import type { DashboardFilters, DrilldownRow } from '@/types/admin'

const { currentUser } = useAuth()
const {
  filterOptions,
  dashboard,
  workload,
  activity,
  trend,
  attentionRows,
  loading,
  error,
  loadFilterOptions,
  refresh,
  drilldown,
} = useAdminDashboard()

const filters = ref<DashboardFilters>({})

const drilldownOpen = ref(false)
const drilldownTitle = ref('')
const drilldownDescription = ref('')
const drilldownRows = ref<DrilldownRow[]>([])
const drilldownLoading = ref(false)
const drilldownOpenProjectsTo = ref<string | undefined>(undefined)

async function initialLoad() {
  await loadFilterOptions()
  await refresh(filters.value)
}

onMounted(() => {
  initialLoad()
  loadRecordCounts()
})

async function onApplyFilters(newFilters: DashboardFilters) {
  filters.value = newFilters
  await refresh(filters.value)
}

// Maps a drill-down context to an existing worklist route, where one
// exists — never invents a new "all projects" page. Left undefined (no
// "Open Projects" button) when nothing in the app already shows that slice.
function routeFor(args: { pending_group?: string; status_key?: string }): string | undefined {
  if (args.pending_group === 'mentor_action_required') return '/sirb/review/mentor'
  if (args.pending_group === 'reviewer_action_required') return '/sirb/review/primary'
  if (args.status_key === 'primary_reviewer') return '/sirb/review/primary'
  if (args.status_key === 'secondary_reviewer') return '/sirb/review/secondary'
  if (args.status_key === 'mentor_approval') return '/sirb/review/mentor'
  return undefined
}

async function openDrilldown(args: {
  irb_unit?: string
  status_key?: string
  pending_group?: string
  role?: string
  faculty?: string
  /** Client-side only — there's no single backend status/group for "every
   * non-approved project", so this excludes Approved rows after fetch
   * instead of inventing a fake pending_group on the server. */
  excludeApproved?: boolean
}) {
  const drillArgs: Parameters<typeof drilldown>[0] = { filters: filters.value }
  const titleParts: string[] = []

  if (args.irb_unit) {
    const p = dashboard.value?.programme_matrix.find((r) => r.irb_unit === args.irb_unit)
    drillArgs.irb_unit = args.irb_unit
    titleParts.push(p?.programme || args.irb_unit)
  }
  if (args.status_key) {
    drillArgs.status = dashboard.value?.status_key_map[args.status_key]
    titleParts.push(args.status_key.replace(/_/g, ' '))
  } else if (args.pending_group) {
    drillArgs.pending_group = args.pending_group
    titleParts.push(args.pending_group.replace(/_/g, ' '))
  } else if (args.role && args.faculty) {
    drillArgs.role_person = { role: args.role, faculty: args.faculty }
    titleParts.push(`${args.role.replace('_', ' ')} workload`)
  } else if (args.excludeApproved) {
    titleParts.push('Pending Work')
  } else if (!args.irb_unit) {
    titleParts.push('All Projects')
  }

  drilldownTitle.value = titleParts.join(' — ')
  drilldownDescription.value = 'Matching project records — search, filter and open any of them below.'
  drilldownOpenProjectsTo.value = routeFor(args)
  drilldownOpen.value = true
  drilldownLoading.value = true
  try {
    const rows = await drilldown(drillArgs)
    drilldownRows.value = args.excludeApproved ? rows.filter((r) => r.status !== 'Approved') : rows
  } finally {
    drilldownLoading.value = false
  }
}

// Rolls the 10 granular statuses into the 5 stages of the pipeline
// visualization — same underlying real counts as the KPI cards and
// programme table, just grouped by "whose court is the project in".
const pipelineStages = computed<PipelineStage[]>(() => {
  const c = dashboard.value?.status_counts
  if (!c) return []
  return [
    { key: 'student_action_required', label: 'Student', count: c.student_action + c.mentor_correction + c.reviewer_correction, icon: 'user' },
    { key: 'mentor_action_required', label: 'Mentor', count: c.mentor_approval, icon: 'user-check' },
    { key: 'primary_review', label: 'Primary Review', count: c.primary_reviewer + c.reviewer_feedback, icon: 'eye' },
    { key: 'secondary_review', label: 'Secondary Review', count: c.secondary_reviewer, icon: 'eye' },
    { key: 'final_approval_required', label: 'Final Approval', count: c.final_approval + c.provisional, icon: 'flag' },
  ]
})

function onPipelineSelect(key: string) {
  if (key === 'primary_review') openDrilldown({ status_key: 'primary_reviewer' })
  else if (key === 'secondary_review') openDrilldown({ status_key: 'secondary_reviewer' })
  else openDrilldown({ pending_group: key })
}

// ---- Manage Records counts --------------------------------------------
// One lightweight COUNT query per doctype (frappe.client.get_count),
// fetched once in parallel — not per-card network calls, and this
// section's own failure never blocks the rest of the dashboard.
interface ManagedCard {
  label: string
  description: string
  icon: string
  slug: string
  doctype: ManagedDoctype
}
const managedCards: ManagedCard[] = [
  { label: 'Academic Organizational Units', description: 'Universities, campuses, schools, departments and programmes.', icon: 'layers', slug: 'academic-organizational-unit', doctype: 'Academic Organizational Unit' },
  { label: 'IRB Units', description: 'Review committees per academic unit, reviewer counts, mentor requirement.', icon: 'shield', slug: 'irb-unit', doctype: 'IRB Unit' },
  { label: 'IRB Projects', description: 'Every submitted project and its current review status.', icon: 'file-text', slug: 'irb-project', doctype: 'IRB Project' },
  { label: 'Faculty', description: 'Faculty records and their linked user accounts.', icon: 'user-check', slug: 'faculty', doctype: 'Faculty' },
  { label: 'Students', description: 'Student records and their linked user accounts.', icon: 'users', slug: 'student', doctype: 'Student' },
  { label: 'Faculty ↔ AO Unit Mapping', description: 'Which academic unit(s) each faculty member belongs to.', icon: 'link', slug: 'faculty-academic-organizational-unit', doctype: 'Faculty Academic Organizational Unit' },
  { label: 'Student Project Mapping', description: 'Which student(s) are attached to each project.', icon: 'git-branch', slug: 'student-project-mapping', doctype: 'Student Project Mapping' },
]
const recordCounts = ref<Partial<Record<ManagedDoctype, number>>>({})
const recordCountsLoading = ref(true)
const recordCountsError = ref<ApiError | null>(null)

async function loadRecordCounts() {
  recordCountsLoading.value = true
  recordCountsError.value = null
  try {
    recordCounts.value = await fetchRecordCounts()
  } catch (e) {
    recordCountsError.value = e instanceof ApiError ? e : new ApiError('Failed to load record counts.', 'server')
  } finally {
    recordCountsLoading.value = false
  }
}
</script>

<template>
  <AppShell>
    <DashboardGreeting
      :name="currentUser?.full_name.split(' ')[0] || 'Administrator'"
      subtitle="Here's what's happening across student project approvals."
    />

    <LoadingState v-if="loading && !dashboard" label="Loading dashboard…" />
    <ErrorState v-else-if="error" :error="error" @retry="initialLoad" />
    <template v-else-if="dashboard && workload && filterOptions">
      <FilterBar :options="filterOptions" @apply="onApplyFilters" />

      <div class="mb-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Projects"
          :value="dashboard.total_projects"
          icon="folder"
          :support="dashboard.new_projects_last_30_days ? `+${dashboard.new_projects_last_30_days} in the last 30 days` : 'None in the last 30 days'"
          action-label="View Projects"
          clickable
          @click="openDrilldown({})"
        />
        <KpiCard
          label="Pending Work"
          :value="dashboard.total_projects - dashboard.status_counts.approved"
          icon="clock"
          tone="warning"
          :support="`${attentionRows.length} waiting over 7 days`"
          action-label="View Projects"
          clickable
          @click="openDrilldown({ excludeApproved: true })"
        />
        <KpiCard
          label="In Review"
          :value="dashboard.status_counts.primary_reviewer + dashboard.status_counts.secondary_reviewer + dashboard.status_counts.reviewer_feedback"
          icon="eye"
          tone="info"
          support="With primary or secondary reviewers"
          action-label="View Projects"
          clickable
          @click="openDrilldown({ pending_group: 'reviewer_action_required' })"
        />
        <KpiCard
          label="Approved"
          :value="dashboard.status_counts.approved"
          icon="check-circle"
          tone="success"
          :support="dashboard.approved_last_30_days ? `+${dashboard.approved_last_30_days} in the last 30 days` : 'None in the last 30 days'"
          action-label="View Projects"
          clickable
          @click="openDrilldown({ status_key: 'approved' })"
        />
      </div>

      <div class="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Student Action"
          :value="dashboard.status_counts.student_action + dashboard.status_counts.mentor_correction + dashboard.status_counts.reviewer_correction"
          icon="user"
          tone="warning"
          support="Awaiting the student"
          clickable
          @click="openDrilldown({ pending_group: 'student_action_required' })"
        />
        <KpiCard
          label="Mentor Review"
          :value="dashboard.status_counts.mentor_approval"
          icon="user-check"
          tone="warning"
          support="Awaiting the faculty mentor"
          clickable
          @click="openDrilldown({ status_key: 'mentor_approval' })"
        />
        <KpiCard
          label="Primary Review"
          :value="dashboard.status_counts.primary_reviewer"
          icon="eye"
          tone="info"
          support="Awaiting the primary reviewer"
          clickable
          @click="openDrilldown({ status_key: 'primary_reviewer' })"
        />
        <KpiCard
          label="Secondary Review"
          :value="dashboard.status_counts.secondary_reviewer"
          icon="eye"
          tone="info"
          support="Awaiting the secondary reviewer"
          clickable
          @click="openDrilldown({ status_key: 'secondary_reviewer' })"
        />
      </div>

      <div class="mb-5">
        <PipelineFlow :stages="pipelineStages" @select="onPipelineSelect" />
      </div>

      <div class="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <TrendChart :points="trend" />
        <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
          <h3 class="text-base font-semibold text-charcoal">Workflow Distribution</h3>
          <p class="mb-2 text-sm text-muted">How many projects sit in each stage today.</p>
          <WorkflowChart :status-counts="dashboard.status_counts" />
        </div>
      </div>

      <div class="mb-5">
        <AttentionList :rows="attentionRows" />
      </div>

      <div class="mb-5">
        <ProgrammeAnalyticsTable :rows="dashboard.programme_matrix" @drill="openDrilldown" />
      </div>

      <div class="mb-5">
        <RoleWorkloadPanel :workload="workload" @drill="(d) => openDrilldown(d)" />
      </div>

      <div class="mb-5">
        <ActivityFeed :activity="activity" />
      </div>

      <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
        <div class="mb-4 flex items-center justify-between gap-2">
          <div>
            <h3 class="text-base font-semibold text-charcoal">Manage Records</h3>
            <p class="text-sm text-muted">
              Create, edit or browse the underlying records. Opens in Frappe Desk, respecting your permissions.
            </p>
          </div>
          <ErrorState v-if="recordCountsError" :error="recordCountsError" @retry="loadRecordCounts" />
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <a
            v-for="dt in managedCards"
            :key="dt.slug"
            :href="`/app/${dt.slug}`"
            target="_blank"
            rel="noopener"
            class="group flex flex-col gap-3 rounded-lg border border-line p-4 transition-colors hover:border-primary hover:bg-canvas"
          >
            <span class="flex h-9 w-9 items-center justify-center rounded-md bg-primary/5 text-primary">
              <FeatherIcon :name="dt.icon" class="h-4.5 w-4.5" />
            </span>
            <div>
              <p v-if="recordCountsLoading" class="h-7 w-12 animate-pulse rounded bg-canvas" />
              <p v-else class="text-2xl font-semibold text-charcoal">{{ recordCounts[dt.doctype] ?? '—' }}</p>
              <p class="mt-1 flex items-center gap-1 text-sm font-medium text-charcoal">{{ dt.label }}</p>
              <p class="mt-0.5 text-xs text-muted">{{ dt.description }}</p>
            </div>
            <p class="flex items-center gap-1 text-xs font-medium text-primary">
              View records
              <FeatherIcon name="arrow-right" class="h-3 w-3" />
            </p>
          </a>
        </div>
      </div>

      <DrilldownDialog
        v-model="drilldownOpen"
        :title="drilldownTitle"
        :description="drilldownDescription"
        :rows="drilldownRows"
        :loading="drilldownLoading"
        :open-projects-to="drilldownOpenProjectsTo"
      />
    </template>
  </AppShell>
</template>
