<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ProgrammeMatrixRow } from '@/types/admin'

const STATUS_SHORT_LABELS: Record<string, string> = {
  student_action: 'Student',
  mentor_approval: 'Mentor',
  mentor_correction: 'Mentor Fix',
  primary_reviewer: 'Primary',
  secondary_reviewer: 'Secondary',
  reviewer_feedback: 'Rev. Feedback',
  reviewer_correction: 'Rev. Fix',
  provisional: 'Provisional',
  final_approval: 'Final',
  approved: 'Approved',
}

const props = defineProps<{ rows: ProgrammeMatrixRow[] }>()
const emit = defineEmits<{ drill: [{ irb_unit?: string; status_key?: string }] }>()

const search = ref('')
const keys = Object.keys(STATUS_SHORT_LABELS)

const filteredRows = computed(() => {
  if (!search.value.trim()) return props.rows
  const term = search.value.trim().toLowerCase()
  return props.rows.filter((r) => (r.programme || r.irb_unit || '').toLowerCase().includes(term))
})
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-sm font-semibold text-gray-900">Workflow by Programme</h3>
      <input
        v-model="search"
        type="text"
        placeholder="Search programme..."
        class="w-56 rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:border-gray-400 focus:outline-none"
      />
    </div>
    <div class="overflow-x-auto">
      <table class="w-full whitespace-nowrap text-left text-xs">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="sticky left-0 bg-gray-50 px-3 py-2 font-medium">Programme</th>
            <th class="px-3 py-2 font-medium">Total</th>
            <th v-for="k in keys" :key="k" class="px-3 py-2 font-medium">{{ STATUS_SHORT_LABELS[k] }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="!filteredRows.length">
            <td :colspan="keys.length + 2" class="px-3 py-6 text-center text-gray-400">No matching programmes.</td>
          </tr>
          <tr v-for="row in filteredRows" :key="row.irb_unit" class="hover:bg-gray-50">
            <td class="sticky left-0 bg-white px-3 py-2 font-medium text-gray-900">
              {{ row.programme || row.irb_unit }}
            </td>
            <td class="px-3 py-2">
              <button class="font-semibold text-indigo-600 hover:underline" @click="emit('drill', { irb_unit: row.irb_unit })">
                {{ row.total }}
              </button>
            </td>
            <td v-for="k in keys" :key="k" class="px-3 py-2">
              <button
                class="hover:underline"
                :class="row.statuses[k] ? 'font-medium text-gray-900' : 'text-gray-400'"
                @click="emit('drill', { irb_unit: row.irb_unit, status_key: k })"
              >
                {{ row.statuses[k] || 0 }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
