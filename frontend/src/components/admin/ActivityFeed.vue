<script setup lang="ts">
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import type { ActivityRow } from '@/types/admin'

defineProps<{ activity: ActivityRow[] }>()
const router = useRouter()

function open(row: ActivityRow) {
  router.push({ name: 'project-details', params: { name: row.project_id } })
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">Recent Activity</h3>
    <EmptyState v-if="!activity.length" icon="activity" title="No recent status changes" />
    <div v-else class="overflow-x-auto">
      <table class="w-full whitespace-nowrap text-left text-xs">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-3 py-2 font-medium">Student(s)</th>
            <th class="px-3 py-2 font-medium">Programme</th>
            <th class="px-3 py-2 font-medium">Action</th>
            <th class="px-3 py-2 font-medium">By</th>
            <th class="px-3 py-2 font-medium">Date</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="(row, i) in activity" :key="i" class="cursor-pointer hover:bg-gray-50" @click="open(row)">
            <td class="px-3 py-2">{{ row.student_names || '—' }}</td>
            <td class="px-3 py-2">{{ row.programme || '—' }}</td>
            <td class="px-3 py-2">{{ row.from_status }} → <b>{{ row.to_status }}</b></td>
            <td class="px-3 py-2">{{ row.performed_by || '—' }}</td>
            <td class="px-3 py-2">{{ new Date(row.date).toLocaleDateString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
