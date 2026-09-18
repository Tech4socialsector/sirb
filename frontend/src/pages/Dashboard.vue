<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import SummaryCard from '@/components/dashboard/SummaryCard.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import { useAuth } from '@/composables/useAuth'
import { useRoles } from '@/composables/useRoles'
import { fetchMyPendingCounts } from '@/services/projects'

const { currentUser } = useAuth()
const { isStudent, isFacultyMentor, isPrimaryReviewer, isSecondaryReviewer, isAdmin, isAnchor } = useRoles()

const counts = ref<Record<string, number>>({})
const loading = ref(true)

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
    <PageHeader
      :title="`Welcome${currentUser ? ', ' + currentUser.full_name.split(' ')[0] : ''}`"
      description="Here's an overview of what needs your attention."
    />

    <LoadingState v-if="loading" />
    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <SummaryCard
        v-if="isStudent"
        label="My Projects"
        :value="counts.student_projects ?? 0"
        icon="file-text"
        to="/sirb/my-projects"
      />
      <SummaryCard
        v-if="isFacultyMentor || isAdmin"
        label="Awaiting My Mentor Approval"
        :value="counts.mentor_pending ?? 0"
        icon="user-check"
        tone="warning"
        to="/sirb/review/mentor"
      />
      <SummaryCard
        v-if="isPrimaryReviewer || isAdmin"
        label="Awaiting My Primary Review"
        :value="counts.primary_reviewer_pending ?? 0"
        icon="check-square"
        tone="warning"
        to="/sirb/review/primary"
      />
      <SummaryCard
        v-if="isSecondaryReviewer || isAdmin"
        label="Awaiting My Secondary Review"
        :value="counts.secondary_reviewer_pending ?? 0"
        icon="check-square"
        tone="warning"
        to="/sirb/review/secondary"
      />
      <SummaryCard v-if="isAdmin" label="Admin Console" value="Open" icon="grid" to="/sirb/admin" />
      <SummaryCard v-if="isAnchor" label="Anchor Reports" value="Open" icon="bar-chart-2" to="/sirb/admin/reports" />
    </div>

    <div
      v-if="
        !loading &&
        !isStudent &&
        !isFacultyMentor &&
        !isPrimaryReviewer &&
        !isSecondaryReviewer &&
        !isAdmin &&
        !isAnchor
      "
      class="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500"
    >
      No SIRB workflows are currently assigned to your account.
    </div>
  </AppShell>
</template>
