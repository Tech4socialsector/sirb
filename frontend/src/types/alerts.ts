import type { FilterOptions } from './admin'

export type AlertFrequency = 'Once' | 'Daily' | 'Weekly' | 'Monthly'
export type RunStatus = 'Queued' | 'Running' | 'Completed' | 'Completed with errors' | 'No recipients' | 'Failed'

export interface AlertFilters {
  /** "students": exactly the picked `student` list; every other key is ignored. */
  mode?: 'students'
  student?: string[]
  campus?: string[]
  /** Any Academic Organizational Unit, matching everything under it (set by Remind). */
  org_unit?: string[]
  irb_unit?: string[]
  academic_year?: string[]
  irb_cycle?: string[]
  status?: string[]
  faculty_mentor?: string[]
  /** Only projects not updated for at least this many days. */
  inactive_days?: number
}

export interface EmailTemplateOption {
  name: string
  subject: string | null
}

export interface TimelineAlert {
  name: string
  alert_name: string
  enabled: 0 | 1
  email_template: string
  filters: AlertFilters
  frequency: AlertFrequency
  start_at: string
  end_date: string | null
  next_run_at: string | null
  last_run_at: string | null
  last_run: string | null
  last_run_status: RunStatus | null
  last_run_sent: number | null
  is_running: boolean
  modified: string
  timeline: string | null
  milestone: string | null
  deadline_label: string | null
  /** Linked timeline is inactive: scheduled sends are skipped. */
  timeline_inactive: boolean
}

export interface AlertInput {
  name?: string
  alert_name: string
  email_template: string
  filters: AlertFilters
  frequency: AlertFrequency
  /** "YYYY-MM-DDTHH:MM" (server timezone). */
  start_at: string
  end_date: string | null
  enabled: 0 | 1
  timeline?: string | null
  milestone?: string | null
}

export interface AlertEnvironment {
  email_configured: boolean
  scheduler_active: boolean
  email_muted: boolean
  timezone: string
  server_now: string
}

export interface AlertPageData {
  filter_options: FilterOptions
  templates: EmailTemplateOption[]
  alerts: TimelineAlert[]
  timelines: IrbTimeline[]
  units: UnitOption[]
  environment: AlertEnvironment
}

export interface UnitOption {
  name: string
  ao_name: string
  ao_type: string
  path: string
}

export interface TimelineMilestone {
  name?: string
  activity: string
  start_date: string
  end_date: string | null
  time_note: string | null
  /** Project statuses Remind targets (empty = every status). */
  remind_statuses: string[]
  /** Server-computed: end date of a range, else the date. */
  deadline?: string
  reminders?: number
  active_reminders?: number
}

export interface IrbTimeline {
  name: string
  timeline_name: string
  ao_unit: string | null
  unit_name: string | null
  unit_type: string | null
  irb_cycle: string | null
  is_active: 0 | 1
  notes: string | null
  milestones: TimelineMilestone[]
}

export interface TimelineInput {
  name?: string
  timeline_name: string
  ao_unit: string | null
  irb_cycle: string | null
  is_active: 0 | 1
  notes: string | null
  milestones: TimelineMilestone[]
}

/** An alert's link to one timeline activity (fills the deadline variables). */
export interface DeadlineLink {
  timeline: string
  milestone: string
  timelineName: string
  activity: string
  deadline: string
  timeNote: string | null
}

export interface RecipientRow {
  student: string
  student_name: string
  student_id: string | null
  email: string
  irb_project: string
  project_title: string | null
  project_status: string
  programme: string
  project_modified: string
  reason: string | null
}

export interface RecipientPreview {
  sendable_count: number
  skipped_count: number
  unique_students: number
  sendable: RecipientRow[]
  skipped: RecipientRow[]
  row_limit: number
  /** E-mails per project status for the same filters *without* the status filter. */
  status_counts: Record<string, number>
}

export interface EmailPreview {
  subject: string
  html: string
  recipient: { student_name: string; email: string } | null
  /** Variables the template uses that don't exist (sending refuses these). */
  unknown_variables: string[]
  /** Uses deadline variables but no timeline activity is linked (sending refuses it). */
  needs_deadline: boolean
}

export interface AlertRun {
  name: string
  alert: string | null
  alert_name: string
  trigger: 'Manual' | 'Scheduled'
  triggered_by: string
  status: RunStatus
  email_template: string
  total_recipients: number
  sent_count: number
  skipped_count: number
  failed_count: number
  creation: string
  started_at: string | null
  finished_at: string | null
  error: string | null
  deadline_label: string | null
}

export interface AlertRunRecipient {
  idx: number
  student: string
  student_name: string
  email: string | null
  irb_project: string
  status: 'Queued' | 'Skipped' | 'Failed'
  reason: string | null
}

export interface AlertRunDetail extends AlertRun {
  filters: AlertFilters
  triggered_by_name: string | null
  recipients: AlertRunRecipient[]
}

/** A student in the recipient picker (one row per student, projects summarised). */
export interface StudentOption {
  student: string
  student_name: string
  student_id: string | null
  academic_year?: string | null
  email: string | null
  user_enabled: 0 | 1
  programme: string | null
  project_count: number
}

/** A row read from a pasted timeline table. */
export interface ParsedActivity {
  activity: string
  start_date: string | null
  end_date: string | null
  time_note: string | null
  /** Why the date couldn't be read; the row is still added, for a manual fix. */
  problem: string | null
}
