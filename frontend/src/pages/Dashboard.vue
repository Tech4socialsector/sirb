<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DashboardGreeting from '@/components/dashboard/DashboardGreeting.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import ProjectListTable from '@/components/projects/ProjectListTable.vue'
import { useAuth } from '@/composables/useAuth'
import { useRoles } from '@/composables/useRoles'
import { ApiError } from '@/services/api'
import { fetchMyDashboard, type DashboardPayload, type DashboardRoleSummary } from '@/services/projects'

const { currentUser } = useAuth()
const { isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isAdmin, isAnchor } = useRoles()

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

const ROLE_COPY: Record<DashboardRoleSummary['key'], { title: string; pending: string; icon: string }> = {
  mentor: { title: 'Mentor Review', pending: 'Awaiting Your Approval', icon: 'user-check' },
  primary_reviewer: { title: 'Primary Review', pending: 'Awaiting Your Review', icon: 'eye' },
  secondary_reviewer: { title: 'Secondary Review', pending: 'Awaiting Your Review', icon: 'eye' },
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

const totalNeedsAction = computed(() => roles.value.reduce((a, r) => a + r.counts.pending, 0))
const subtitle = computed(() => {
  if (loading.value || error.value || !roles.value.length) return "Here's an overview of your SIRB work."
  if (!totalNeedsAction.value) return "You're all caught up. Nothing is waiting on you right now."
  const n = totalNeedsAction.value
  return `${n} project${n === 1 ? ' is' : 's are'} waiting on you.`
})

const hasAnything = computed(() => roles.value.length > 0 || !!student.value || isAdmin.value || isAnchor.value)

function tabLink(route: string, tab: 'pending' | 'unapproved' | 'approved') {
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
      <div v-if="isAdmin || isAnchor" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard v-if="isAdmin" label="Admin Console" value="Open" icon="grid" action-label="Go to console" to="/sirb/admin" />
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

      <!-- One section per mentor / reviewer role -->
      <section v-for="role in roles" :key="role.key">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-lg font-semibold text-charcoal">{{ ROLE_COPY[role.key].title }}</h2>
          <RouterLink :to="role.route" class="flex items-center gap-1 text-sm font-medium text-primary hover:underline">
            Open worklist
            <FeatherIcon name="arrow-right" class="h-3.5 w-3.5" />
          </RouterLink>
        </div>
        <div class="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <KpiCard
            :label="ROLE_COPY[role.key].pending"
            :value="role.counts.pending"
            :icon="ROLE_COPY[role.key].icon"
            :tone="role.counts.pending ? 'warning' : 'default'"
            :support="role.counts.pending ? 'Waiting on you' : 'All caught up'"
            action-label="View Pending"
            :to="tabLink(role.route, 'pending')"
          />
          <KpiCard
            label="In Progress"
            :value="role.counts.in_progress"
            icon="clock"
            tone="info"
            support="Assigned to you, not yet approved"
            action-label="View In Progress"
            :to="tabLink(role.route, 'unapproved')"
          />
          <KpiCard
            label="Approved"
            :value="role.counts.approved"
            icon="check-circle"
            tone="success"
            support="Fully approved projects"
            action-label="View Approved"
            :to="tabLink(role.route, 'approved')"
          />
        </div>
        <h3 class="mb-2 text-sm font-semibold text-muted">Recently updated</h3>
        <ProjectListTable
          :rows="role.recent"
          empty-title="No active projects"
          empty-description="Projects assigned to you will appear here."
        />
      </section>

      <div v-if="!hasAnything" class="rounded-lg border border-line bg-paper p-8 text-center text-sm text-muted">
        No SIRB workflows are currently assigned to your account.
      </div>
    </div>
  </AppShell>
</template>
