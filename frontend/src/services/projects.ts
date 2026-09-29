import { call } from './api'
import type {
  FieldChangeEntry,
  ProjectDetailPayload,
  ProjectListRow,
  ProposalIssue,
  StatusChangeEntry,
} from '@/types/project'

export function fetchStudentProjects() {
  return call<ProjectListRow[]>('sirb.sirb_api.worklists.get_student_projects')
}

export type WorklistBucket = 'pending' | 'unapproved' | 'approved'

export function fetchMentorProjects(bucket: WorklistBucket = 'pending') {
  return call<ProjectListRow[]>('sirb.sirb_api.worklists.get_mentor_projects', { bucket })
}

export function fetchPrimaryReviewerProjects(bucket: WorklistBucket = 'pending') {
  return call<ProjectListRow[]>('sirb.sirb_api.worklists.get_primary_reviewer_projects', { bucket })
}

export function fetchSecondaryReviewerProjects(bucket: WorklistBucket = 'pending') {
  return call<ProjectListRow[]>('sirb.sirb_api.worklists.get_secondary_reviewer_projects', { bucket })
}

export interface DashboardRoleSummary {
  key: 'mentor' | 'primary_reviewer' | 'secondary_reviewer'
  route: string
  counts: { pending: number; in_progress: number; approved: number }
  recent: (ProjectListRow & { needs_action: boolean })[]
}

export interface DashboardPayload {
  roles: DashboardRoleSummary[]
  student: { total: number; group: number; approved: number } | null
}

export function fetchMyDashboard() {
  return call<DashboardPayload>('sirb.sirb_api.worklists.get_my_dashboard')
}

export function fetchProjectDetail(projectName: string) {
  return call<ProjectDetailPayload>('sirb.sirb_api.project.get_project_detail', {
    project_name: projectName,
  })
}

export function fetchStatusChangeHistory(projectName: string) {
  return call<StatusChangeEntry[]>('sirb.sirb_api.project.get_status_change_history', {
    project_name: projectName,
  })
}

export function fetchFieldChangesSinceStatus(projectName: string, sinceStatus: string) {
  return call<Record<string, FieldChangeEntry[]>>('sirb.sirb_api.project.get_field_changes_since_status', {
    project_name: projectName,
    since_status: sinceStatus,
  })
}

export function setProjectStatus(projectId: string, status: string) {
  return call<{ message: string }>('sirb.api.set_project_status', { project_id: projectId, status })
}

export function saveProjectFields(projectName: string, fields: Record<string, unknown>) {
  return call('frappe.client.set_value', {
    doctype: 'IRB Project',
    name: projectName,
    fieldname: fields,
  })
}

export function fetchProposalIssues(projectName: string) {
  return call<ProposalIssue[]>('sirb.sirb_api.project.get_proposal_issues', { project_name: projectName })
}
