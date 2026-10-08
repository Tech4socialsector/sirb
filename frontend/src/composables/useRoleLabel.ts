import { computed, ref } from 'vue'
import { useRoles } from './useRoles'
import type { ProjectRoles } from '@/types/project'

/** The user's roles on the project page that's open, set by that page
 * (null elsewhere). Faculty roles are site-wide — one person can mentor
 * one project and review another — so on a project page the label shows
 * the role they hold on it, not whichever global role ranks first. */
const projectRoles = ref<ProjectRoles | null>(null)

export function setProjectRoles(roles: ProjectRoles | null) {
  projectRoles.value = roles
}

/** Single human-readable "primary role" label, shared between UserMenu and
 * the Profile page so the two never drift out of sync on how a role is
 * named. Precedence: Admin > role on the open project > Student > Mentor >
 * Primary > Secondary > Programme Manager > Programme Viewer. */
export function useRoleLabel() {
  const { isAdmin, isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isProgrammeViewer, isProgrammeManager } =
    useRoles()

  const roleLabel = computed(() => {
    if (isAdmin.value) return 'Administrator'
    const project = projectRoles.value
    if (project?.is_student) return 'Student'
    if (project?.is_mentor) return 'Faculty Mentor'
    if (project?.is_primary_reviewer) return 'Primary Reviewer'
    if (project?.is_secondary_reviewer) return 'Secondary Reviewer'
    if (isStudent.value) return 'Student'
    if (isFacultyMentor.value) return 'Faculty Mentor'
    if (isPrimaryReviewer.value) return 'Primary Reviewer'
    if (isSecondaryReviewer.value) return 'Secondary Reviewer'
    if (isProgrammeManager.value) return 'Programme Manager'
    if (isProgrammeViewer.value) return 'Programme Viewer'
    return 'User'
  })

  return { roleLabel }
}
