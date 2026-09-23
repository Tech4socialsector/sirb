<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import DashboardGreeting from '@/components/dashboard/DashboardGreeting.vue'
import KpiCard from '@/components/dashboard/KpiCard.vue'
import { useAuth } from '@/composables/useAuth'
import { useRoles } from '@/composables/useRoles'
import { fetchMyPendingCounts } from '@/services/projects'

const router = useRouter()
const { currentUser } = useAuth()
const { isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isAdmin, isAnchor } = useRoles()

const counts = ref<Record<string, number>>({})
const loading = ref(true)

const hasAnyWork = computed(
  () => isStudent.value || isFacultyMentor.value || isPrimaryReviewer.value || isSecondaryReviewer.value || isAdmin.value || isAnchor.value,
)

const studentProjectsSupport = computed(() => {
  const total = counts.value.student_projects ?? 0
  if (!total) return undefined
  const group = counts.value.student_group_projects ?? 0
  return `${total - group} individual · ${group} group`
})

onMounted(async () => {
  try {
    counts.value = await fetchMyPendingCounts()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <AppShell>
    <DashboardGreeting
      :name="currentUser?.full_name.split(' ')[0] || 'there'"
      subtitle="Here's an overview of what needs your attention."
    />

    <LoadingState v-if="loading" label="Loading your dashboard…" />
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        v-if="isStudent"
        label="My Projects"
        :value="counts.student_projects ?? 0"
        :support="studentProjectsSupport"
        icon="folder"
        action-label="View Projects"
        clickable
        @click="router.push('/sirb/my-projects')"
      />
      <KpiCard
        v-if="isFacultyMentor"
        label="Awaiting Mentor Approval"
        :value="counts.mentor_pending ?? 0"
        icon="user-check"
        tone="warning"
        action-label="View All"
        clickable
        @click="router.push('/sirb/review/mentor')"
      />
      <KpiCard
        v-if="isPrimaryReviewer"
        label="Awaiting Primary Review"
        :value="counts.primary_reviewer_pending ?? 0"
        icon="eye"
        tone="info"
        action-label="View All"
        clickable
        @click="router.push('/sirb/review/primary')"
      />
      <KpiCard
        v-if="isSecondaryReviewer"
        label="Awaiting Secondary Review"
        :value="counts.secondary_reviewer_pending ?? 0"
        icon="eye"
        tone="info"
        action-label="View All"
        clickable
        @click="router.push('/sirb/review/secondary')"
      />
      <KpiCard v-if="isAdmin" label="Admin Console" value="Open" icon="grid" clickable @click="router.push('/sirb/admin')" />
      <KpiCard v-if="isAnchor" label="Reports" value="Open" icon="bar-chart-2" clickable @click="router.push('/sirb/admin/reports')" />
    </div>

    <div
      v-if="!loading && !hasAnyWork"
      class="rounded-lg border border-line bg-paper p-8 text-center text-sm text-muted"
    >
      No SIRB workflows are currently assigned to your account.
    </div>
  </AppShell>
</template>
