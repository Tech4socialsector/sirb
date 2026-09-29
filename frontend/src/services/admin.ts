import { call } from './api'
import type {
  ActivityRow,
  DashboardData,
  DashboardFilters,
  DrilldownRow,
  FilterOptions,
  RoleWorkload,
  TrendPoint,
} from '@/types/admin'

const NS = 'sirb.sirb.page.irb_admin_console.irb_admin_console'

export function fetchFilterOptions() {
  return call<FilterOptions>(`${NS}.get_filter_options`)
}

export function fetchDashboardData(filters: DashboardFilters) {
  return call<DashboardData>(`${NS}.get_dashboard_data`, { filters })
}

export function fetchRoleWorkload(filters: DashboardFilters) {
  return call<RoleWorkload>(`${NS}.get_role_workload`, { filters })
}

export function fetchProjectTrend(filters: DashboardFilters, months = 6) {
  return call<TrendPoint[]>(`${NS}.get_project_trend`, { filters, months })
}

export function fetchRecentActivity(filters: DashboardFilters, limit = 25) {
  return call<ActivityRow[]>(`${NS}.get_recent_activity`, { filters, limit })
}

export interface DrilldownArgs {
  filters?: DashboardFilters
  status?: string
  irb_unit?: string
  pending_group?: string
  role_person?: { role: string; faculty: string }
  /** Several STATUS_KEY_MAP keys at once, for cards that sum statuses. */
  status_keys?: string[]
  /** One row per project (members aggregated) instead of per student. */
  per_project?: boolean
}

export function fetchDrilldownStudents(args: DrilldownArgs) {
  return call<DrilldownRow[]>(`${NS}.get_drilldown_students`, args as Record<string, unknown>)
}
