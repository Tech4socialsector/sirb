<script setup lang="ts">
import { onMounted } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectListTable from '@/components/projects/ProjectListTable.vue'
import WorklistTabs from '@/components/projects/WorklistTabs.vue'
import { useProjects } from '@/composables/useProjects'
import { fetchMentorProjects } from '@/services/projects'

const { rows, loading, error, bucket, counts, load } = useProjects(fetchMentorProjects)

onMounted(() => load())
</script>

<template>
  <AppShell>
    <PageHeader title="Mentor Worklist" description="Projects where you are the assigned faculty mentor." />
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :error="error" @retry="() => load()" />
    <ProjectListTable v-else :rows="rows" empty-title="No projects in this bucket">
      <template #tabs>
        <WorklistTabs v-model="bucket" :counts="counts" />
      </template>
    </ProjectListTable>
  </AppShell>
</template>
