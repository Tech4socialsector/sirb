import { call } from './api'
import type {
  FieldChangeEntry,
  ProjectDetailPayload,
  ProjectListRow,
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

export function fetchMyPendingCounts() {
  return call<Record<string, number>>('sirb.sirb_api.worklists.get_my_pending_counts')
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
