export const PROJECT_STATUSES = [
  'Awaiting proposal completion by student',
  'Awaiting Faculty mentor approval',
  'Awaiting student correction for mentor feedback',
  'Awaiting primary reviewer comments to secondary reviewer',
  'Awaiting secondary reviewer comments to primary reviewer',
  'Awaiting reviewer feedback to student',
  'Awaiting student correction for reviewer feedback',
  'Provisionally approved',
  'Awaiting final approval',
  'Approved',
] as const

export type ProjectStatus = (typeof PROJECT_STATUSES)[number]

export interface ProjectListRow {
  project_id?: string
  project_name?: string
  project_title: string
  project_status: ProjectStatus | string
  irb_cycle?: string
  last_updated?: string
  student_id?: string
  /** Worklists: every active member, comma-separated (one row per project). */
  student_name?: string
  /** Number of students mapped to the project; > 1 means a group project. */
  student_count?: number
  /** My Projects only: the other members of a group project. */
  teammates?: string | null
}

export interface ProjectRoles {
  is_student: boolean
  is_mentor: boolean
  is_primary_reviewer: boolean
  is_secondary_reviewer: boolean
}

export interface ProjectStudent {
  student_id: string
  full_name: string
  user_email: string
}

export interface IrbProjectDoc {
  name: string
  title: string
  topic?: string
  abstract?: string
  status: ProjectStatus | string
  irb_unit: string
  irb_cycle?: string
  project_domain?: string
  primary_reviewer?: string
  secondary_reviewer?: string
  faculty_mentor?: string
  num_reviewers?: string | number
  i_hereby_confirm_the_above?: number
  [key: string]: unknown
}

export interface ProjectDetailPayload {
  doc: IrbProjectDoc
  link_titles: Record<string, string>
  roles: ProjectRoles
  students: ProjectStudent[]
  meta: { can_write: boolean }
}

export interface StatusChangeEntry {
  from_status: string
  to_status: string
  changed_by: string
  date: string
}

export interface FieldChangeEntry {
  old_value: unknown
  new_value: unknown
  date: string
}
