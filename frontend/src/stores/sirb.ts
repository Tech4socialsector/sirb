import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DashboardFilters } from '@/types/admin'

export const useSirbStore = defineStore('sirb', () => {
  const adminFilters = ref<DashboardFilters>({})

  function setAdminFilters(filters: DashboardFilters) {
    adminFilters.value = filters
  }

  function clearAdminFilters() {
    adminFilters.value = {}
  }

  return { adminFilters, setAdminFilters, clearAdminFilters }
})
