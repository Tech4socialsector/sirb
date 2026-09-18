<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import { useRoles } from '@/composables/useRoles'

interface NavItem {
  label: string
  to: string
  icon: string
}

const { isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isAnchor, isAdmin } = useRoles()

const items = computed<NavItem[]>(() => {
  const list: NavItem[] = [{ label: 'Dashboard', to: '/sirb', icon: 'home' }]

  if (isStudent.value) {
    list.push({ label: 'My Projects', to: '/sirb/my-projects', icon: 'file-text' })
  }
  if (isFacultyMentor.value || isAdmin.value) {
    list.push({ label: 'Mentor Worklist', to: '/sirb/review/mentor', icon: 'users' })
  }
  if (isPrimaryReviewer.value || isAdmin.value) {
    list.push({ label: 'Primary Review', to: '/sirb/review/primary', icon: 'check-square' })
  }
  if (isSecondaryReviewer.value || isAdmin.value) {
    list.push({ label: 'Secondary Review', to: '/sirb/review/secondary', icon: 'check-square' })
  }
  if (isAdmin.value) {
    list.push({ label: 'Admin Console', to: '/sirb/admin', icon: 'grid' })
  }
  if (isAnchor.value) {
    list.push({ label: 'Reports', to: '/sirb/admin/reports', icon: 'bar-chart-2' })
    list.push({ label: 'Upload Students', to: '/sirb/uploads/students', icon: 'upload' })
    list.push({ label: 'Upload Faculty', to: '/sirb/uploads/faculty', icon: 'upload' })
  }

  return list
})
</script>

<template>
  <nav class="flex flex-col gap-1 p-3">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100"
      active-class="!bg-gray-900 !text-white"
      exact-active-class="!bg-gray-900 !text-white"
    >
      <FeatherIcon :name="item.icon" class="h-4 w-4 shrink-0" />
      <span class="truncate">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>
