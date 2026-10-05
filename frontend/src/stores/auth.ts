import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchCurrentUser } from '@/services/auth'
import type { CurrentUser } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<CurrentUser | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const initialized = ref(false)

  const roles = computed(() => new Set(currentUser.value?.roles ?? []))

  function hasRole(...anyOf: string[]) {
    return anyOf.some((r) => roles.value.has(r))
  }

  const isAdmin = computed(() => hasRole('System Manager', 'Administrator'))
  const isAnchor = computed(() => hasRole('Anchor') || isAdmin.value)
  const isStudent = computed(() => currentUser.value?.is_student ?? false)
  const isFacultyMentor = computed(() => hasRole('Faculty Mentor'))
  const isPrimaryReviewer = computed(() => hasRole('Primary IRB Reviewer'))
  const isSecondaryReviewer = computed(() => hasRole('Secondary IRB Reviewer'))
  const isFaculty = computed(() => currentUser.value?.is_faculty ?? false)
  // Admin Console for the programmes on their IRB Programme Access record —
  // the server scopes every console query to those. Viewers: read only.
  // Managers: can also open those programmes' projects to reassign the
  // mentor/reviewers and set the status (enforced server-side).
  const isProgrammeManager = computed(() => hasRole('IRB Programme Manager') && !isAdmin.value)
  const isProgrammeViewer = computed(() => hasRole('IRB Programme Viewer') && !isAdmin.value && !isProgrammeManager.value)
  const canViewAdminConsole = computed(() => isAdmin.value || isProgrammeViewer.value || isProgrammeManager.value)
  // May open projects from the console (the server still decides per project).
  const canOpenConsoleProjects = computed(() => isAdmin.value || isProgrammeManager.value)
  // Nothing in SIRB but the console (and, for managers, its projects): no
  // Home dashboard or worklists.
  const isConsoleOnly = computed(
    () =>
      (isProgrammeViewer.value || isProgrammeManager.value) &&
      !isAnchor.value &&
      !isStudent.value &&
      !isFaculty.value &&
      !hasRole('Student', 'Faculty Mentor', 'Primary IRB Reviewer', 'Secondary IRB Reviewer'),
  )
  // Console only, and read only: no project records at all.
  const isViewerOnly = computed(() => isConsoleOnly.value && isProgrammeViewer.value)

  async function load() {
    if (initialized.value) return
    loading.value = true
    error.value = null
    try {
      currentUser.value = await fetchCurrentUser()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load session'
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  return {
    currentUser,
    loading,
    error,
    initialized,
    roles,
    hasRole,
    isAdmin,
    isAnchor,
    isStudent,
    isFacultyMentor,
    isPrimaryReviewer,
    isSecondaryReviewer,
    isFaculty,
    isProgrammeViewer,
    isProgrammeManager,
    canViewAdminConsole,
    canOpenConsoleProjects,
    isConsoleOnly,
    isViewerOnly,
    load,
  }
})
