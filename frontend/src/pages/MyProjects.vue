<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectListTable from '@/components/projects/ProjectListTable.vue'
import { fetchStudentProjects } from '@/services/projects'
import { ApiError } from '@/services/api'
import type { ProjectListRow } from '@/types/project'

const rows = ref<ProjectListRow[]>([])
const loading = ref(true)
const error = ref<ApiError | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    rows.value = await fetchStudentProjects()
  } catch (e) {
    error.value = e instanceof ApiError ? e : new ApiError('Failed to load your projects.', 'server')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <PageHeader title="My IRB Projects" description="Projects you've submitted for ethics review." />
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <ProjectListTable
      v-else
      :rows="rows"
      empty-title="No IRB projects yet"
      empty-description="Once a project is created for you, it will appear here."
    />
  </AppShell>
</template>
