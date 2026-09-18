<script setup lang="ts">
import { useRouter } from 'vue-router'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { ProjectListRow } from '@/types/project'

const props = defineProps<{
  rows: ProjectListRow[]
  emptyTitle?: string
  emptyDescription?: string
}>()

const router = useRouter()

function openProject(row: ProjectListRow) {
  const name = row.project_id || row.project_name
  if (name) router.push({ name: 'project-details', params: { name } })
}
</script>

<template>
  <EmptyState
    v-if="!rows.length"
    icon="inbox"
    :title="emptyTitle || 'No projects found'"
    :description="emptyDescription"
  />
  <div v-else class="overflow-hidden rounded-lg border border-gray-200 bg-white">
    <!-- Desktop table -->
    <table class="hidden w-full text-left text-sm md:table">
      <thead class="border-b border-gray-200 bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
        <tr>
          <th v-if="rows[0]?.student_name" class="px-4 py-2.5 font-medium">Student</th>
          <th class="px-4 py-2.5 font-medium">Project</th>
          <th class="px-4 py-2.5 font-medium">Cycle</th>
          <th class="px-4 py-2.5 font-medium">Status</th>
          <th class="px-4 py-2.5 font-medium">Updated</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        <tr
          v-for="row in props.rows"
          :key="row.project_id || row.project_name"
          class="cursor-pointer hover:bg-gray-50"
          @click="openProject(row)"
        >
          <td v-if="row.student_name" class="px-4 py-3 text-gray-700">{{ row.student_name }}</td>
          <td class="px-4 py-3 font-medium text-gray-900">{{ row.project_title || '(Untitled)' }}</td>
          <td class="px-4 py-3 text-gray-500">{{ row.irb_cycle || '—' }}</td>
          <td class="px-4 py-3"><StatusBadge :status="row.project_status" /></td>
          <td class="px-4 py-3 text-gray-500">
            {{ row.last_updated ? new Date(row.last_updated).toLocaleDateString() : '—' }}
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Mobile cards -->
    <div class="divide-y divide-gray-100 md:hidden">
      <button
        v-for="row in props.rows"
        :key="row.project_id || row.project_name"
        class="flex w-full flex-col gap-1.5 p-4 text-left"
        @click="openProject(row)"
      >
        <span v-if="row.student_name" class="text-xs text-gray-500">{{ row.student_name }}</span>
        <span class="font-medium text-gray-900">{{ row.project_title || '(Untitled)' }}</span>
        <div class="flex items-center justify-between">
          <StatusBadge :status="row.project_status" />
          <span class="text-xs text-gray-400">{{ row.irb_cycle }}</span>
        </div>
      </button>
    </div>
  </div>
</template>
