<script setup lang="ts">
import { Button, Dialog } from 'frappe-ui'
import { useRouter } from 'vue-router'
import type { DrilldownRow } from '@/types/admin'

const props = defineProps<{
  modelValue: boolean
  title: string
  rows: DrilldownRow[]
}>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const router = useRouter()

function open(row: DrilldownRow) {
  emit('update:modelValue', false)
  router.push({ name: 'project-details', params: { name: row.project_id } })
}

function exportCsv() {
  const header = [
    'Student Name',
    'Student ID',
    'Programme',
    'Status',
    'Faculty Mentor',
    'Primary Reviewer',
    'Secondary Reviewer',
    'Last Updated',
  ]
  const lines = [header.join(',')]
  for (const r of props.rows) {
    lines.push(
      [
        r.student_name,
        r.student_id,
        r.programme,
        r.status,
        r.faculty_mentor || '',
        r.primary_reviewer || '',
        r.secondary_reviewer || '',
        r.last_updated,
      ]
        .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`)
        .join(','),
    )
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.title.replace(/[\\/:*?"<>|]/g, '-')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <Dialog
    :model-value="modelValue"
    :options="{ title: `${title} (${rows.length})`, size: '5xl' }"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <template #body-content>
      <div class="max-h-[60vh] overflow-auto">
        <table class="w-full whitespace-nowrap text-left text-xs">
          <thead class="sticky top-0 bg-gray-50 text-gray-500">
            <tr>
              <th class="px-3 py-2 font-medium">Student</th>
              <th class="px-3 py-2 font-medium">ID</th>
              <th class="px-3 py-2 font-medium">Programme</th>
              <th class="px-3 py-2 font-medium">Status</th>
              <th class="px-3 py-2 font-medium">Mentor</th>
              <th class="px-3 py-2 font-medium">Primary</th>
              <th class="px-3 py-2 font-medium">Secondary</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-if="!rows.length">
              <td colspan="7" class="px-3 py-6 text-center text-gray-400">No matching students.</td>
            </tr>
            <tr v-for="row in rows" :key="row.project_id" class="cursor-pointer hover:bg-gray-50" @click="open(row)">
              <td class="px-3 py-2">{{ row.student_name || '—' }}</td>
              <td class="px-3 py-2">{{ row.student_id || '—' }}</td>
              <td class="px-3 py-2">{{ row.programme || '—' }}</td>
              <td class="px-3 py-2">{{ row.status || '—' }}</td>
              <td class="px-3 py-2">{{ row.faculty_mentor || '—' }}</td>
              <td class="px-3 py-2">{{ row.primary_reviewer || '—' }}</td>
              <td class="px-3 py-2">{{ row.secondary_reviewer || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <template #actions>
      <Button variant="outline" @click="exportCsv">Export CSV</Button>
    </template>
  </Dialog>
</template>
