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
    load,
  }
})
