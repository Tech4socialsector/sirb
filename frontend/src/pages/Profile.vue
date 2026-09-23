<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Avatar, Badge } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import { useAuth } from '@/composables/useAuth'
import { useRoleLabel } from '@/composables/useRoleLabel'
import { fetchMyProfile, type FacultyRecord, type StudentRecord } from '@/services/profile'

const { currentUser } = useAuth()
const { roleLabel } = useRoleLabel()

const student = ref<StudentRecord | null>(null)
const faculty = ref<FacultyRecord | null>(null)
const loadingDetail = ref(false)

onMounted(async () => {
  if (!currentUser.value) return
  loadingDetail.value = true
  try {
    if (currentUser.value.is_student || currentUser.value.is_faculty) {
      const profile = await fetchMyProfile()
      student.value = profile.student
      faculty.value = profile.faculty
    }
  } catch {
    // Profile detail is a nice-to-have supplement to the session data
    // already shown above — a failed lookup shouldn't block the page.
  } finally {
    loadingDetail.value = false
  }
})

const roleBadges = computed(() => currentUser.value?.roles.filter((r) => r !== 'All') ?? [])
</script>

<template>
  <AppShell>
    <PageHeader title="Profile" description="Your account details in SIRB." />

    <LoadingState v-if="!currentUser" label="Loading profile…" />
    <template v-else>
      <div class="mb-4 flex items-center gap-4 rounded-lg border border-line bg-paper p-5 shadow-card">
        <Avatar :label="currentUser.full_name" size="2xl" />
        <div class="min-w-0">
          <h2 class="text-lg font-semibold text-charcoal">{{ currentUser.full_name }}</h2>
          <p class="text-sm text-muted">{{ currentUser.user }}</p>
          <Badge class="mt-2" theme="gray" variant="subtle">{{ roleLabel }}</Badge>
        </div>
      </div>

      <div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div class="rounded-lg border border-line bg-paper p-5 shadow-card">
          <h3 class="mb-4 text-sm font-semibold text-charcoal">Personal Information</h3>
          <dl class="space-y-3 text-sm">
            <div class="flex justify-between gap-3">
              <dt class="text-muted">Full Name</dt>
              <dd class="font-medium text-charcoal">{{ currentUser.full_name }}</dd>
            </div>
            <div class="flex justify-between gap-3">
              <dt class="text-muted">Email</dt>
              <dd class="truncate font-medium text-charcoal">{{ currentUser.user }}</dd>
            </div>
            <div v-if="student" class="flex justify-between gap-3">
              <dt class="text-muted">Academic Year</dt>
              <dd class="font-medium text-charcoal">{{ student.academic_year || '—' }}</dd>
            </div>
          </dl>
        </div>

        <div class="rounded-lg border border-line bg-paper p-5 shadow-card">
          <h3 class="mb-4 text-sm font-semibold text-charcoal">
            {{ currentUser.is_student ? 'Academic Information' : 'Professional Information' }}
          </h3>
          <dl v-if="!loadingDetail" class="space-y-3 text-sm">
            <div v-if="student" class="flex justify-between gap-3">
              <dt class="text-muted">Student ID</dt>
              <dd class="font-medium text-charcoal">{{ student.student_id }}</dd>
            </div>
            <div v-if="faculty" class="flex justify-between gap-3">
              <dt class="text-muted">Faculty Record</dt>
              <dd class="font-medium text-charcoal">{{ faculty.full_name }}</dd>
            </div>
            <div v-if="!student && !faculty" class="text-muted">
              No Student or Faculty record is linked to this account.
            </div>
          </dl>
          <p v-else class="text-sm text-muted">Loading…</p>
        </div>
      </div>

      <div class="rounded-lg border border-line bg-paper p-5 shadow-card">
        <h3 class="mb-4 text-sm font-semibold text-charcoal">Account &amp; Roles</h3>
        <div class="flex flex-wrap gap-2">
          <Badge v-for="role in roleBadges" :key="role" theme="gray" variant="subtle">{{ role }}</Badge>
        </div>
      </div>
    </template>
  </AppShell>
</template>
