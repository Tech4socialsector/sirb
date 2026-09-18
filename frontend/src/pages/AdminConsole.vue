<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import SummaryCard from '@/components/dashboard/SummaryCard.vue'
import FilterBar from '@/components/admin/FilterBar.vue'
import ProgrammeMatrix from '@/components/admin/ProgrammeMatrix.vue'
import WorkflowChart from '@/components/dashboard/WorkflowChart.vue'
import PendingActionsList from '@/components/admin/PendingActionsList.vue'
import RoleWorkloadPanel from '@/components/admin/RoleWorkloadPanel.vue'
import ActivityFeed from '@/components/admin/ActivityFeed.vue'
import DrilldownDialog from '@/components/admin/DrilldownDialog.vue'
import { useAdminDashboard } from '@/composables/useAdminDashboard'
import type { DashboardFilters } from '@/types/admin'
import type { DrilldownRow } from '@/types/admin'

const { filterOptions, dashboard, workload, activity, loading, error, loadFilterOptions, refresh, drilldown } =
  useAdminDashboard()

const filters = ref<DashboardFilters>({})

const drilldownOpen = ref(false)
const drilldownTitle = ref('')
const drilldownRows = ref<DrilldownRow[]>([])

async function initialLoad() {
  await loadFilterOptions()
  await refresh(filters.value)
}

onMounted(initialLoad)

async function onApplyFilters(newFilters: DashboardFilters) {
  filters.value = newFilters
  await refresh(filters.value)
}

async function openDrilldown(args: { irb_unit?: string; status_key?: string; pending_group?: string; role?: string; faculty?: string }) {
  const drillArgs: Parameters<typeof drilldown>[0] = { filters: filters.value }
  const titleParts: string[] = []

  if (args.irb_unit) {
    const p = dashboard.value?.programme_matrix.find((r) => r.irb_unit === args.irb_unit)
    drillArgs.irb_unit = args.irb_unit
    titleParts.push(p?.programme || args.irb_unit)
  }
  if (args.status_key) {
    drillArgs.status = dashboard.value?.status_key_map[args.status_key]
    titleParts.push(args.status_key)
  } else if (args.pending_group) {
    drillArgs.pending_group = args.pending_group
    titleParts.push(args.pending_group.replace(/_/g, ' '))
  } else if (args.role && args.faculty) {
    drillArgs.role_person = { role: args.role, faculty: args.faculty }
    titleParts.push(`${args.role.replace('_', ' ')} workload`)
  } else if (!args.irb_unit) {
    titleParts.push('All Students')
  }

  drilldownTitle.value = titleParts.join(' — ')
  drilldownRows.value = await drilldown(drillArgs)
  drilldownOpen.value = true
}
</script>

<template>
  <AppShell>
    <PageHeader title="IRB Admin Console" description="Live overview of the review workflow across all programmes." />

    <LoadingState v-if="loading && !dashboard" label="Loading dashboard…" />
    <ErrorState v-else-if="error" :error="error" @retry="initialLoad" />
    <template v-else-if="dashboard && workload && filterOptions">
      <FilterBar :options="filterOptions" @apply="onApplyFilters" />

      <div class="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
        <SummaryCard label="Total Students" :value="dashboard.total_students" icon="users" @click="openDrilldown({})" />
        <SummaryCard
          label="Student Action"
          :value="dashboard.pending_actions.student_action_required"
          icon="user"
          tone="warning"
          @click="openDrilldown({ pending_group: 'student_action_required' })"
        />
        <SummaryCard
          label="Faculty Mentor"
          :value="dashboard.pending_actions.mentor_action_required"
          icon="user-check"
          tone="warning"
          @click="openDrilldown({ pending_group: 'mentor_action_required' })"
        />
        <SummaryCard
          label="Reviewer"
          :value="dashboard.pending_actions.reviewer_action_required"
          icon="eye"
          tone="warning"
          @click="openDrilldown({ pending_group: 'reviewer_action_required' })"
        />
        <SummaryCard
          label="Final Approval"
          :value="dashboard.pending_actions.final_approval_required"
          icon="flag"
          tone="warning"
          @click="openDrilldown({ pending_group: 'final_approval_required' })"
        />
        <SummaryCard
          label="Provisional"
          :value="dashboard.status_counts.provisional"
          icon="check-circle"
          tone="success"
          @click="openDrilldown({ status_key: 'provisional' })"
        />
        <SummaryCard
          label="Approved"
          :value="dashboard.status_counts.approved"
          icon="check"
          tone="success"
          @click="openDrilldown({ status_key: 'approved' })"
        />
      </div>

      <div class="mb-5">
        <ProgrammeMatrix :rows="dashboard.programme_matrix" @drill="openDrilldown" />
      </div>

      <div class="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div class="rounded-lg border border-gray-200 bg-white p-5">
          <h3 class="mb-4 text-sm font-semibold text-gray-900">Workflow Distribution</h3>
          <WorkflowChart :status-counts="dashboard.status_counts" />
        </div>
        <PendingActionsList
          :pending-actions="dashboard.pending_actions"
          @drill="(group) => openDrilldown({ pending_group: group })"
        />
      </div>

      <div class="mb-5">
        <RoleWorkloadPanel :workload="workload" @drill="(d) => openDrilldown(d)" />
      </div>

      <ActivityFeed :activity="activity" />

      <DrilldownDialog v-model="drilldownOpen" :title="drilldownTitle" :rows="drilldownRows" />
    </template>
  </AppShell>
</template>
