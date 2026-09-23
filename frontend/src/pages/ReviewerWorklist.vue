<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectListTable from '@/components/projects/ProjectListTable.vue'
import WorklistTabs from '@/components/projects/WorklistTabs.vue'
import { useProjects } from '@/composables/useProjects'
import { fetchPrimaryReviewerProjects, fetchSecondaryReviewerProjects } from '@/services/projects'

const props = defineProps<{ role: 'primary' | 'secondary' }>()

const fetcher = computed(() =>
  props.role === 'primary' ? fetchPrimaryReviewerProjects : fetchSecondaryReviewerProjects,
)
const title = computed(() => (props.role === 'primary' ? 'Primary Reviewer Worklist' : 'Secondary Reviewer Worklist'))

const { rows, loading, error, bucket, counts, load } = useProjects((b) => fetcher.value(b))

onMounted(() => load())
watch(
  () => props.role,
  () => load(),
)
</script>

<template>
  <AppShell>
    <PageHeader :title="title" description="Projects assigned to you for review." />
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :error="error" @retry="() => load()" />
    <ProjectListTable v-else :rows="rows" empty-title="No projects in this bucket">
      <template #tabs>
        <WorklistTabs v-model="bucket" :counts="counts" />
      </template>
    </ProjectListTable>
  </AppShell>
</template>
