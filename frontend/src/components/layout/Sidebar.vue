<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import UserMenu from './UserMenu.vue'
import { useRoles } from '@/composables/useRoles'

defineProps<{ mobile?: boolean }>()
defineEmits<{ navigate: [] }>()

interface NavItem {
  label: string
  to: string
  icon: string
}
interface NavGroup {
  label: string | null
  items: NavItem[]
}

const { isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isAnchor, isAdmin } = useRoles()

// Every entry here maps to a route that already exists in router/index.ts —
// this only groups/relabels the existing pages per role, it does not
// introduce new pages per role (see architecture note: one shared
// ProjectDetails.vue + role-scoped worklists, not five separate apps).
const groups = computed<NavGroup[]>(() => {
  const list: NavGroup[] = [{ label: null, items: [{ label: 'Dashboard', to: '/sirb', icon: 'home' }] }]

  const myWork: NavItem[] = []
  if (isStudent.value) myWork.push({ label: 'My Projects', to: '/sirb/my-projects', icon: 'file-text' })
  if (isFacultyMentor.value || isAdmin.value)
    myWork.push({ label: 'Mentor Worklist', to: '/sirb/review/mentor', icon: 'users' })
  if (isPrimaryReviewer.value || isAdmin.value)
    myWork.push({ label: 'Primary Review', to: '/sirb/review/primary', icon: 'check-square' })
  if (isSecondaryReviewer.value || isAdmin.value)
    myWork.push({ label: 'Secondary Review', to: '/sirb/review/secondary', icon: 'check-square' })
  if (myWork.length) list.push({ label: 'My Work', items: myWork })

  const admin: NavItem[] = []
  if (isAdmin.value) {
    admin.push({ label: 'Admin Console', to: '/sirb/admin', icon: 'grid' })
    admin.push({ label: 'Setup', to: '/sirb/admin/setup', icon: 'settings' })
    admin.push({ label: 'Student & Project Management', to: '/sirb/admin/students', icon: 'users' })
  }
  if (isAnchor.value) {
    admin.push({ label: 'Reports', to: '/sirb/admin/reports', icon: 'bar-chart-2' })
    admin.push({ label: 'Upload Students', to: '/sirb/uploads/students', icon: 'upload' })
    admin.push({ label: 'Upload Faculty', to: '/sirb/uploads/faculty', icon: 'upload' })
  }
  if (admin.length) list.push({ label: 'Administration', items: admin })

  return list
})
</script>

<template>
  <aside
    class="flex h-full flex-col bg-paper"
    :class="mobile ? 'w-72' : 'hidden w-64 shrink-0 border-r border-line md:flex'"
  >
    <div class="flex h-16 shrink-0 items-center gap-2.5 border-b border-line px-4">
      <div class="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-xs font-bold text-white">
        IRB
      </div>
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold text-charcoal">SIRB</p>
        <p class="truncate text-[11px] text-muted">Student Project Approvals</p>
      </div>
    </div>

    <nav class="flex-1 space-y-5 overflow-y-auto sirb-scrollbar p-3">
      <div v-for="(group, gi) in groups" :key="gi">
        <p v-if="group.label" class="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wide text-muted">
          {{ group.label }}
        </p>
        <div class="flex flex-col gap-0.5">
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-charcoal/80 transition-colors hover:bg-canvas hover:text-charcoal"
            active-class="!bg-primary !text-white"
            exact-active-class="!bg-primary !text-white"
            @click="$emit('navigate')"
          >
            <FeatherIcon :name="item.icon" class="h-4 w-4 shrink-0" />
            <span class="truncate">{{ item.label }}</span>
          </RouterLink>
        </div>
      </div>
    </nav>

    <div class="shrink-0 border-t border-line p-3">
      <UserMenu />
    </div>
  </aside>
</template>
