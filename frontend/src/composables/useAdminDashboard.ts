import { ref } from 'vue'
import {
  fetchDashboardData,
  fetchDrilldownStudents,
  fetchFilterOptions,
  fetchRecentActivity,
  fetchRoleWorkload,
  type DrilldownArgs,
} from '@/services/admin'
import { ApiError } from '@/services/api'
import type { ActivityRow, DashboardData, DashboardFilters, FilterOptions, RoleWorkload } from '@/types/admin'

export function useAdminDashboard() {
  const filterOptions = ref<FilterOptions | null>(null)
  const dashboard = ref<DashboardData | null>(null)
  const workload = ref<RoleWorkload | null>(null)
  const activity = ref<ActivityRow[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)

  async function loadFilterOptions() {
    filterOptions.value = await fetchFilterOptions()
  }

  async function refresh(filters: DashboardFilters) {
    loading.value = true
    error.value = null
    try {
      const [dashboardData, workloadData, activityData] = await Promise.all([
        fetchDashboardData(filters),
        fetchRoleWorkload(filters),
        fetchRecentActivity(filters),
      ])
      dashboard.value = dashboardData
      workload.value = workloadData
      activity.value = activityData
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError('Failed to load the dashboard.', 'server')
    } finally {
      loading.value = false
    }
  }

  async function drilldown(args: DrilldownArgs) {
    return fetchDrilldownStudents(args)
  }

  return { filterOptions, dashboard, workload, activity, loading, error, loadFilterOptions, refresh, drilldown }
}
