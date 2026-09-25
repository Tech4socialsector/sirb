import { call } from './api'
import type {
  AlertFilters,
  AlertInput,
  AlertPageData,
  AlertRun,
  AlertRunDetail,
  EmailPreview,
  EmailTemplateOption,
  IrbTimeline,
  ParsedActivity,
  RecipientPreview,
  StudentOption,
  TimelineAlert,
  TimelineInput,
} from '@/types/alerts'

const NS = 'sirb.sirb_api.timeline_alerts'

export function fetchAlertPageData() {
  return call<AlertPageData>(`${NS}.get_page_data`)
}

export function fetchTemplates() {
  return call<EmailTemplateOption[]>(`${NS}.get_templates`)
}

export function fetchAlerts() {
  return call<TimelineAlert[]>(`${NS}.get_alerts`)
}

/** With `timeline`, the server scopes recipients to its current unit and cycle. */
export function previewRecipients(filters: AlertFilters, timeline: string | null = null) {
  return call<RecipientPreview>(`${NS}.preview_recipients`, { filters, timeline })
}

type Link = { timeline: string; milestone: string } | null

export function previewEmail(emailTemplate: string, filters: AlertFilters, link: Link = null) {
  return call<EmailPreview>(`${NS}.preview_email`, {
    email_template: emailTemplate,
    filters,
    timeline: link?.timeline ?? null,
    milestone: link?.milestone ?? null,
  })
}

/** `requestId` makes the call idempotent: repeating it returns the same run. */
export function sendNow(emailTemplate: string, filters: AlertFilters, requestId: string, link: Link = null) {
  return call<string>(`${NS}.send_now`, {
    email_template: emailTemplate,
    filters,
    request_id: requestId,
    timeline: link?.timeline ?? null,
    milestone: link?.milestone ?? null,
  })
}

export function saveAlert(data: AlertInput) {
  return call<string>(`${NS}.save_alert`, { data })
}

export function setAlertEnabled(name: string, enabled: boolean) {
  return call<{ enabled: 0 | 1; next_run_at: string | null }>(`${NS}.set_alert_enabled`, { name, enabled: enabled ? 1 : 0 })
}

export function runAlertNow(name: string) {
  return call<string>(`${NS}.run_alert_now`, { name })
}

export function deleteAlert(name: string) {
  return call<void>(`${NS}.delete_alert`, { name })
}

export function fetchRuns(limit = 50) {
  return call<AlertRun[]>(`${NS}.get_runs`, { limit })
}

export function fetchRun(name: string) {
  return call<AlertRunDetail>(`${NS}.get_run`, { name })
}

export function searchStudents(txt: string) {
  return call<StudentOption[]>(`${NS}.search_students`, { txt })
}

export function fetchStudentLabels(names: string[]) {
  return call<StudentOption[]>(`${NS}.get_student_labels`, { names })
}

const TL = 'sirb.sirb_api.irb_timelines'

export function fetchTimelines() {
  return call<IrbTimeline[]>(`${TL}.get_timelines`)
}

export function saveTimeline(data: TimelineInput) {
  return call<string>(`${TL}.save_timeline`, { data })
}

export function deleteTimeline(name: string) {
  return call<void>(`${TL}.delete_timeline`, { name })
}

export function parseActivities(text: string) {
  return call<{ rows: ParsedActivity[]; title: string | null }>(`${TL}.parse_activities`, { text })
}
