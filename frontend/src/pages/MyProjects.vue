<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectListTable from '@/components/projects/ProjectListTable.vue'
import { fetchStudentProjects } from '@/services/projects'
import { ApiError } from '@/services/api'
import type { ProjectListRow } from '@/types/project'

type Tab = 'individual' | 'group'

const route = useRoute()
const router = useRouter()

const rows = ref<ProjectListRow[]>([])
const loading = ref(true)
const error = ref<ApiError | null>(null)

// A project is a group project when more than one student is mapped to it.
const groupRows = computed(() => rows.value.filter((r) => Number(r.student_count) > 1))
const individualRows = computed(() => rows.value.filter((r) => Number(r.student_count) <= 1))

const tabs = computed(() => [
  { value: 'individual' as Tab, label: 'Individual', icon: 'user', count: individualRows.value.length },
  { value: 'group' as Tab, label: 'Group', icon: 'users', count: groupRows.value.length },
])

// The tab lives in the URL (?tab=group) so refresh/back keeps it. Without
// one, open whichever tab actually has projects.
const activeTab = computed<Tab>(() => {
  const q = route.query.tab
  if (q === 'individual' || q === 'group') return q
  return !individualRows.value.length && groupRows.value.length ? 'group' : 'individual'
})

const visibleRows = computed(() => (activeTab.value === 'group' ? groupRows.value : individualRows.value))

function selectTab(tab: Tab) {
  if (tab !== activeTab.value) router.replace({ query: { ...route.query, tab } })
}

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
      :rows="visibleRows"
      :empty-title="activeTab === 'group' ? 'No group projects' : 'No individual projects'"
      :empty-description="
        activeTab === 'group'
          ? 'Projects you share with other students will appear here.'
          : 'Projects where you are the only student will appear here.'
      "
    >
      <template #tabs>
        <div class="flex gap-1 border-b border-line px-6" role="tablist">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            role="tab"
            :aria-selected="activeTab === tab.value"
            class="relative flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors"
            :class="activeTab === tab.value ? 'text-charcoal' : 'text-muted hover:text-charcoal'"
            @click="selectTab(tab.value)"
          >
            <FeatherIcon :name="tab.icon" class="h-4 w-4" />
            {{ tab.label }}
            <span
              class="rounded-full px-2 py-0.5 text-xs font-semibold"
              :class="activeTab === tab.value ? 'bg-primary text-white' : 'bg-canvas text-muted'"
            >
              {{ tab.count }}
            </span>
            <span v-if="activeTab === tab.value" class="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-primary" />
          </button>
        </div>
      </template>
    </ProjectListTable>
  </AppShell>
</template>
