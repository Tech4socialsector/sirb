<script setup lang="ts">
import { onMounted, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectListTable from '@/components/projects/ProjectListTable.vue'
import WorklistTabs from '@/components/projects/WorklistTabs.vue'
import { useProjects } from '@/composables/useProjects'
import { fetchMentorProjects } from '@/services/projects'

const { rows, loading, error, bucket, load } = useProjects(fetchMentorProjects)

onMounted(() => load())
watch(bucket, () => load())
</script>

<template>
  <AppShell>
    <PageHeader title="Mentor Worklist" description="Projects where you are the assigned faculty mentor.">
      <template #actions>
        <WorklistTabs v-model="bucket" />
      </template>
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :error="error" @retry="() => load()" />
    <ProjectListTable v-else :rows="rows" empty-title="No projects in this bucket" />
  </AppShell>
</template>
