import { computed } from 'vue'
import { useRoles } from './useRoles'

/** Single human-readable "primary role" label, shared between UserMenu and
 * the Profile page so the two never drift out of sync on how a role is
 * named. Precedence: Admin > Student > Mentor > Primary > Secondary. */
export function useRoleLabel() {
  const { isAdmin, isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer } = useRoles()

  const roleLabel = computed(() => {
    if (isAdmin.value) return 'Administrator'
    if (isStudent.value) return 'Student'
    if (isFacultyMentor.value) return 'Faculty Mentor'
    if (isPrimaryReviewer.value) return 'Primary Reviewer'
    if (isSecondaryReviewer.value) return 'Secondary Reviewer'
    return 'User'
  })

  return { roleLabel }
}
