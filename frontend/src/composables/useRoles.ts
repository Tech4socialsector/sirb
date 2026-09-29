import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

/**
 * Role-derived flags used to decide what UI to show. This is a UX
 * convenience only — hiding a nav item or action button here never
 * substitutes for the server-side permission check that actually
 * protects the underlying data (see each service's whitelisted method).
 */
export function useRoles() {
  const store = useAuthStore()
  const { isAdmin, isAnchor, isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isFaculty } =
    storeToRefs(store)

  return {
    isAdmin,
    isAnchor,
    isStudent,
    isFacultyMentor,
    isPrimaryReviewer,
    isSecondaryReviewer,
    isFaculty,
    hasRole: store.hasRole,
  }
}
