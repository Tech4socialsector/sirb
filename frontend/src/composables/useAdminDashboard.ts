import { computed, ref } from 'vue'
import {
  fetchDashboardData,
  fetchDrilldownStudents,
  fetchFilterOptions,
  fetchProjectTrend,
  fetchRecentActivity,
  fetchRoleWorkload,
  type DrilldownArgs,
} from '@/services/admin'
import { ApiError } from '@/services/api'
import type {
  ActivityRow,
  DashboardData,
  DashboardFilters,
  DrilldownRow,
  FilterOptions,
  RoleWorkload,
  TrendPoint,
} from '@/types/admin'

const ATTENTION_THRESHOLD_DAYS = 7

export interface AttentionRow extends DrilldownRow {
  days_waiting: number
}

export function useAdminDashboard() {
  const filterOptions = ref<FilterOptions | null>(null)
  const dashboard = ref<DashboardData | null>(null)
  const workload = ref<RoleWorkload | null>(null)
  const activity = ref<ActivityRow[]>([])
  const trend = ref<TrendPoint[]>([])
  const pendingRows = ref<DrilldownRow[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  // Derived client-side from the same pending-project rows the drilldown
  // modal already uses (last_updated + status are already there) — no
  // separate "days waiting" field or endpoint needed.
  const attentionRows = computed<AttentionRow[]>(() => {
    const now = Date.now()
    return pendingRows.value
      .filter((r) => r.status !== 'Approved')
      .map((r) => ({
        ...r,
        days_waiting: Math.floor((now - new Date(r.last_updated).getTime()) / 86400000),
      }))
      .filter((r) => r.days_waiting >= ATTENTION_THRESHOLD_DAYS)
      .sort((a, b) => b.days_waiting - a.days_waiting)
  })

  async function loadFilterOptions() {
    filterOptions.value = await fetchFilterOptions()
  }

  async function refresh(filters: DashboardFilters) {
    loading.value = true
    error.value = null
    try {
      const [dashboardData, workloadData, activityData, trendData, allPendingRows] = await Promise.all([
        fetchDashboardData(filters),
        fetchRoleWorkload(filters),
        fetchRecentActivity(filters),
        fetchProjectTrend(filters),
        fetchDrilldownStudents({ filters, per_project: true }),
      ])
      dashboard.value = dashboardData
      workload.value = workloadData
      activity.value = activityData
      trend.value = trendData
      pendingRows.value = allPendingRows
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError('Failed to load the dashboard.', 'server')
    } finally {
      loading.value = false
    }
  }

  // Per project, so a drill-down lists as many rows as the count clicked
  // (group projects used to appear once per student).
  async function drilldown(args: DrilldownArgs) {
    return fetchDrilldownStudents({ ...args, per_project: true })
  }

  return {
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
  }
}
