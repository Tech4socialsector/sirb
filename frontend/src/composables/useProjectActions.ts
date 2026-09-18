import { computed, type Ref } from 'vue'
import type { IrbProjectDoc, ProjectRoles } from '@/types/project'

export interface ProjectAction {
  label: string
  targetStatus: string
  variant?: 'solid' | 'subtle' | 'outline'
}

/**
 * Reproduces the exact status -> role -> available-actions table from the
 * legacy IRB Project DocType JS (frm.add_custom_button(...) blocks under
 * "Actions"). This is the single source of truth for which buttons render;
 * the server's set_project_status has no independent notion of "valid
 * transition" today, so keeping this table correct is what preserves the
 * existing workflow behavior in the new UI.
 */
export function useProjectActions(
  doc: Ref<IrbProjectDoc | null>,
  roles: Ref<ProjectRoles | null>,
  hasSecondaryReviewer: Ref<boolean>,
) {
  const actions = computed<ProjectAction[]>(() => {
    if (!doc.value || !roles.value) return []
    const status = doc.value.status
    const r = roles.value
    const list: ProjectAction[] = []

    if (r.is_student) {
      if (status === 'Awaiting proposal completion by student') {
        const mentorRequired = Boolean(doc.value.faculty_mentor) || hasSecondaryReviewer.value
        if (mentorRequired) {
          list.push({ label: 'Request Faculty Mentor Approval', targetStatus: 'Awaiting Faculty mentor approval' })
        } else {
          list.push({
            label: 'Request Reviewer Approval',
            targetStatus: hasSecondaryReviewer.value
              ? 'Awaiting primary reviewer comments to secondary reviewer'
              : 'Awaiting reviewer feedback to student',
          })
        }
      } else if (status === 'Awaiting student correction for mentor feedback') {
        list.push({ label: 'Submit corrections', targetStatus: 'Awaiting Faculty mentor approval' })
      } else if (status === 'Awaiting student correction for reviewer feedback') {
        list.push({ label: 'Submit corrections', targetStatus: 'Awaiting reviewer feedback to student' })
      } else if (status === 'Provisionally approved') {
        list.push({ label: 'Submit for final approval', targetStatus: 'Awaiting final approval' })
      }
    } else if (r.is_mentor) {
      if (status === 'Awaiting Faculty mentor approval') {
        const nextStatus = hasSecondaryReviewer.value
          ? 'Awaiting primary reviewer comments to secondary reviewer'
          : 'Awaiting reviewer feedback to student'
        list.push({ label: 'Approve for review', targetStatus: nextStatus })
        list.push({
          label: 'Request corrections from student',
          targetStatus: 'Awaiting student correction for mentor feedback',
          variant: 'outline',
        })
      }
    } else if (r.is_primary_reviewer) {
      if (status === 'Awaiting reviewer feedback to student') {
        list.push({
          label: 'Request corrections from student',
          targetStatus: 'Awaiting student correction for reviewer feedback',
          variant: 'outline',
        })
        list.push({ label: 'Grant FINAL approval', targetStatus: 'Approved' })
        list.push({ label: 'Grant PROVISIONAL approval', targetStatus: 'Provisionally approved', variant: 'subtle' })
      } else if (status === 'Awaiting final approval') {
        list.push({ label: 'Grant FINAL approval', targetStatus: 'Approved' })
      } else if (status === 'Awaiting primary reviewer comments to secondary reviewer') {
        list.push({
          label: 'Forward to secondary reviewer',
          targetStatus: 'Awaiting secondary reviewer comments to primary reviewer',
        })
      } else if (status === 'Provisionally approved') {
        list.push({ label: 'Grant FINAL approval', targetStatus: 'Approved' })
      }
    } else if (r.is_secondary_reviewer) {
      if (status === 'Awaiting secondary reviewer comments to primary reviewer') {
        list.push({ label: 'Forward to primary reviewer', targetStatus: 'Awaiting reviewer feedback to student' })
      }
    }

    return list
  })

  /** Mirrors toggle_save_button(): whether the current status/role
   * combination should allow saving field edits at all. */
  const canEdit = computed<boolean>(() => {
    if (!doc.value || !roles.value) return false
    const status = doc.value.status
    const r = roles.value

    if (r.is_student) {
      return [
        'Awaiting proposal completion by student',
        'Awaiting student correction for mentor feedback',
        'Awaiting student correction for reviewer feedback',
        'Provisionally approved',
        'Approved',
      ].includes(status)
    }
    if (r.is_mentor) {
      return ['Awaiting Faculty mentor approval', 'Approved'].includes(status)
    }
    if (r.is_primary_reviewer) {
      return [
        'Awaiting primary reviewer comments to secondary reviewer',
        'Awaiting reviewer feedback to student',
        'Awaiting final approval',
        'Approved',
      ].includes(status)
    }
    if (r.is_secondary_reviewer) {
      return ['Awaiting secondary reviewer comments to primary reviewer', 'Approved'].includes(status)
    }
    return false
  })

  return { actions, canEdit }
}
