export interface FilterOptions {
  programmes: { name: string; ao_name: string }[]
  academic_years: string[]
  cycles: string[]
  mentors: { name: string; full_name: string }[]
  reviewers: { name: string; full_name: string }[]
  statuses: string[]
}

export interface DashboardFilters {
  irb_unit?: string[]
  academic_year?: string[]
  irb_cycle?: string[]
  faculty_mentor?: string[]
  primary_reviewer?: string[]
  secondary_reviewer?: string[]
  status?: string
  from_date?: string
  to_date?: string
}

export interface ProgrammeMatrixRow {
  irb_unit: string
  programme: string
  total: number
  statuses: Record<string, number>
}

export interface DashboardData {
  total_students: number
  status_counts: Record<string, number>
  pending_actions: Record<string, number>
  programme_matrix: ProgrammeMatrixRow[]
  status_list: string[]
  status_key_map: Record<string, string>
}

export interface RoleWorkloadRow {
  faculty_id: string
  faculty_name: string
  pending_count: number
}

export interface RoleWorkload {
  mentors: RoleWorkloadRow[]
  primary_reviewers: RoleWorkloadRow[]
  secondary_reviewers: RoleWorkloadRow[]
}

export interface ActivityRow {
  project_id: string
  from_status: string
  to_status: string
  performed_by: string
  date: string
  project_title?: string
  programme?: string
  student_names?: string
}

export interface DrilldownRow {
  student_id: string
  student_name: string
  programme: string
  project_id: string
  project_title: string
  status: string
  faculty_mentor?: string
  primary_reviewer?: string
  secondary_reviewer?: string
  last_updated: string
}
