<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DashboardGreeting from '@/components/dashboard/DashboardGreeting.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import RoleCountCard from '@/components/dashboard/RoleCountCard.vue'
import { useAuth } from '@/composables/useAuth'
import { useRoles } from '@/composables/useRoles'
import { ApiError } from '@/services/api'
import { fetchMyDashboard, type DashboardPayload, type DashboardRoleSummary } from '@/services/projects'

const { currentUser } = useAuth()
const { isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isAnchor, canViewAdminConsole } = useRoles()

const data = ref<DashboardPayload | null>(null)
const loading = ref(true)
const error = ref<ApiError | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await fetchMyDashboard()
  } catch (e) {
    error.value = e instanceof ApiError ? e : new ApiError('Failed to load your dashboard.', 'server')
  } finally {
    loading.value = false
  }
}

onMounted(load)

// Column labels, in the Desk workspace's left-to-right order.
const ROLE_LABEL: Record<DashboardRoleSummary['key'], string> = {
  mentor: 'Mentor',
  primary_reviewer: 'Primary Reviewer',
  secondary_reviewer: 'Secondary Reviewer',
}

// The server only returns roles whose faculty record exists; the role
// flags additionally keep the UI in line with the sidebar's own gating.
const roleVisible: Record<DashboardRoleSummary['key'], () => boolean> = {
  mentor: () => isFacultyMentor.value,
  primary_reviewer: () => isPrimaryReviewer.value,
  secondary_reviewer: () => isSecondaryReviewer.value,
}
const roles = computed(() => (data.value?.roles ?? []).filter((r) => roleVisible[r.key]?.()))
const student = computed(() => (isStudent.value ? data.value?.student ?? null : null))

type Bucket = keyof DashboardRoleSummary['counts']
// One row per bucket, as on the Desk "IRB Projects" workspace. Each bucket
// matches the worklist tab of the same name, so a card's number always
// equals the length of the list it opens.
const ROWS: { bucket: Bucket; heading: string; suffix: string }[] = [
  { bucket: 'pending', heading: 'Action needed!', suffix: 'action pending' },
  { bucket: 'unapproved', heading: 'Unapproved - Action not needed', suffix: '- unapproved' },
  { bucket: 'approved', heading: 'Approved', suffix: '- approved' },
]

const totalNeedsAction = computed(() => roles.value.reduce((a, r) => a + r.counts.pending, 0))
const subtitle = computed(() => {
  if (loading.value || error.value || !roles.value.length) return "Here's an overview of your SIRB work."
  if (!totalNeedsAction.value) return "You're all caught up. Nothing is waiting on you right now."
  const n = totalNeedsAction.value
  return `${n} project${n === 1 ? ' is' : 's are'} waiting on you.`
})

const hasAnything = computed(() => roles.value.length > 0 || !!student.value || canViewAdminConsole.value || isAnchor.value)

function tabLink(route: string, tab: Bucket) {
  return tab === 'pending' ? route : { path: route, query: { tab } }
}
</script>

<template>
  <AppShell>
    <DashboardGreeting :name="currentUser?.full_name?.split(' ')[0] || 'there'" :subtitle="subtitle" />

    <LoadingState v-if="loading" label="Loading your dashboard…" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <div v-else class="space-y-8">
      <!-- Admin / Anchor shortcuts -->
      <div v-if="canViewAdminConsole || isAnchor" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard v-if="canViewAdminConsole" label="Admin Console" value="Open" icon="grid" action-label="Go to console" to="/sirb/admin" />
        <KpiCard v-if="isAnchor" label="Reports" value="Open" icon="bar-chart-2" action-label="View reports" to="/sirb/admin/reports" />
      </div>

      <!-- Student -->
      <section v-if="student">
        <h2 class="mb-3 text-lg font-semibold text-charcoal">My Projects</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <KpiCard
            label="My Projects"
            :value="student.total"
            :support="student.total ? `${student.total - student.group} individual · ${student.group} group` : 'No projects yet'"
            icon="folder"
            action-label="View Projects"
            to="/sirb/my-projects"
          />
          <KpiCard
            label="In Progress"
            :value="student.total - student.approved"
            icon="clock"
            tone="info"
            action-label="View Projects"
            to="/sirb/my-projects"
          />
          <KpiCard label="Approved" :value="student.approved" icon="check-circle" tone="success" action-label="View Projects" to="/sirb/my-projects" />
        </div>
      </section>

      <!-- Role based project counts (Desk "IRB Projects" workspace) -->
      <section v-if="roles.length" class="rounded-xl border border-line bg-paper p-5 shadow-card sm:p-6">
        <h2 class="text-lg font-semibold text-charcoal">Role based project counts</h2>
        <p class="mt-2 text-sm leading-relaxed text-muted">
          This section gives you access to all the projects assigned to you against each of your roles, based on
          their status. Click on a card below to view the list of projects for that role, and open any project from
          the list to view its details.
        </p>
        <div v-for="row in ROWS" :key="row.bucket" class="mt-6">
          <h3 class="mb-3 text-base font-semibold text-charcoal">{{ row.heading }}</h3>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <RoleCountCard
              v-for="role in roles"
              :key="role.key"
              :label="`${ROLE_LABEL[role.key]} ${row.suffix}`"
              :value="role.counts[row.bucket]"
              :tone="row.bucket"
              :to="tabLink(role.route, row.bucket)"
            />
          </div>
        </div>
      </section>

      <div v-if="!hasAnything" class="rounded-lg border border-line bg-paper p-8 text-center text-sm text-muted">
        No SIRB workflows are currently assigned to your account.
      </div>
    </div>
  </AppShell>
</template>
