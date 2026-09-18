<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { fetchProjectSummaryByIrbUnit, fetchProjectsByIrbUnit } from '@/services/reports'
import { ApiError } from '@/services/api'

interface SummaryRow {
  irb_unit: string
  project_status: string
  project_count: number
}
interface DetailRow {
  irb_unit: string
  project_status: string
  days_in_state: number
  student_info: string[]
  mentor: string | null
  primary_reviewer: string | null
  secondary_reviewer: string | null
  project_name: string
}

const summaryRows = ref<SummaryRow[]>([])
const detailRows = ref<DetailRow[]>([])
const loading = ref(true)
const error = ref<ApiError | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [summary, detail] = await Promise.all([
      fetchProjectSummaryByIrbUnit() as Promise<{ rows: SummaryRow[] }>,
      fetchProjectsByIrbUnit({}) as Promise<DetailRow[]>,
    ])
    summaryRows.value = summary.rows
    detailRows.value = detail
  } catch (e) {
    error.value = e instanceof ApiError ? e : new ApiError('Failed to load reports.', 'server')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <AppShell>
    <PageHeader title="Anchor Reports" description="Programme-wide project status summary and detail." />
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <template v-else>
      <div class="mb-5 rounded-lg border border-gray-200 bg-white p-5">
        <h3 class="mb-4 text-sm font-semibold text-gray-900">Project Status Summary</h3>
        <EmptyState v-if="!summaryRows.length" icon="bar-chart-2" title="No data yet" />
        <table v-else class="w-full text-left text-sm">
          <thead class="border-b border-gray-200 text-xs uppercase text-gray-500">
            <tr>
              <th class="py-2">Programme</th>
              <th class="py-2">Status</th>
              <th class="py-2">Count</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="(row, i) in summaryRows" :key="i">
              <td class="py-2">{{ row.irb_unit }}</td>
              <td class="py-2">{{ row.project_status }}</td>
              <td class="py-2 font-medium">{{ row.project_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="rounded-lg border border-gray-200 bg-white p-5">
        <h3 class="mb-4 text-sm font-semibold text-gray-900">Project Status Details</h3>
        <EmptyState v-if="!detailRows.length" icon="file-text" title="No active projects" />
        <div v-else class="overflow-x-auto">
          <table class="w-full whitespace-nowrap text-left text-xs">
            <thead class="bg-gray-50 text-gray-500">
              <tr>
                <th class="px-3 py-2 font-medium">Programme</th>
                <th class="px-3 py-2 font-medium">Status</th>
                <th class="px-3 py-2 font-medium">Days in state</th>
                <th class="px-3 py-2 font-medium">Students</th>
                <th class="px-3 py-2 font-medium">Mentor</th>
                <th class="px-3 py-2 font-medium">Primary</th>
                <th class="px-3 py-2 font-medium">Secondary</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="row in detailRows" :key="row.project_name">
                <td class="px-3 py-2">{{ row.irb_unit }}</td>
                <td class="px-3 py-2">{{ row.project_status }}</td>
                <td class="px-3 py-2">{{ row.days_in_state }}</td>
                <td class="px-3 py-2">{{ row.student_info.join(', ') }}</td>
                <td class="px-3 py-2">{{ row.mentor || '—' }}</td>
                <td class="px-3 py-2">{{ row.primary_reviewer || '—' }}</td>
                <td class="px-3 py-2">{{ row.secondary_reviewer || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </AppShell>
</template>
