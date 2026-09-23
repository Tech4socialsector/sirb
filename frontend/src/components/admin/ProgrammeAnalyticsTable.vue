<script setup lang="ts">
import { computed, ref } from 'vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import type { ProgrammeMatrixRow } from '@/types/admin'

const props = defineProps<{ rows: ProgrammeMatrixRow[] }>()
const emit = defineEmits<{ drill: [{ irb_unit?: string; status_key?: string }] }>()

const search = ref('')

// There is no "Rejected" status in this workflow (see IRB Project's status
// options) — a rejection outcome doesn't exist here, only "returned for
// correction", so that column is intentionally omitted rather than shown
// as a fake always-zero metric.
const summarized = computed(() =>
  props.rows.map((r) => ({
    ...r,
    student_action: r.statuses.student_action || 0,
    mentor_review: r.statuses.mentor_approval || 0,
    primary_review: r.statuses.primary_reviewer || 0,
    secondary_review: r.statuses.secondary_reviewer || 0,
    approved: r.statuses.approved || 0,
    returned: (r.statuses.mentor_correction || 0) + (r.statuses.reviewer_correction || 0),
  })),
)

const filteredRows = computed(() => {
  if (!search.value.trim()) return summarized.value
  const term = search.value.trim().toLowerCase()
  return summarized.value.filter((r) => (r.programme || r.irb_unit || '').toLowerCase().includes(term))
})

type SummarizedRow = (typeof summarized)['value'][number]
function asRow(row: Record<string, unknown>) {
  return row as unknown as SummarizedRow
}

const columns: DataTableColumn[] = [
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'total', label: 'Total', align: 'right', sortable: true },
  { key: 'student_action', label: 'Student Action', align: 'right', sortable: true },
  { key: 'mentor_review', label: 'Mentor Review', align: 'right', sortable: true },
  { key: 'primary_review', label: 'Primary Review', align: 'right', sortable: true },
  { key: 'secondary_review', label: 'Secondary Review', align: 'right', sortable: true },
  { key: 'approved', label: 'Approved', align: 'right', sortable: true },
  { key: 'returned', label: 'Returned', align: 'right', sortable: true },
]
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 class="text-base font-semibold text-charcoal">Programme Analytics</h3>
        <p class="text-sm text-muted">Where each programme's projects stand right now.</p>
      </div>
      <input
        v-model="search"
        type="text"
        placeholder="Search programme…"
        class="w-56 rounded-md border border-line bg-canvas px-3 py-1.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none"
      />
    </div>

    <DataTable
      :columns="columns"
      :rows="filteredRows as unknown as Record<string, unknown>[]"
      row-key="irb_unit"
      empty-title="No matching programmes"
    >
      <template #cell-programme="{ row }">
        <span class="font-medium text-charcoal">{{ asRow(row).programme || asRow(row).irb_unit }}</span>
      </template>
      <template #cell-total="{ row, value }">
        <button
          class="font-semibold text-primary hover:underline"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit })"
        >
          {{ value }}
        </button>
      </template>
      <template #cell-student_action="{ row, value }">
        <button
          v-if="(value as number) > 0"
          class="hover:underline"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit, status_key: 'student_action' })"
        >
          {{ value }}
        </button>
        <span v-else class="text-muted">0</span>
      </template>
      <template #cell-mentor_review="{ row, value }">
        <button
          v-if="(value as number) > 0"
          class="hover:underline"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit, status_key: 'mentor_approval' })"
        >
          {{ value }}
        </button>
        <span v-else class="text-muted">0</span>
      </template>
      <template #cell-primary_review="{ row, value }">
        <button
          v-if="(value as number) > 0"
          class="hover:underline"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit, status_key: 'primary_reviewer' })"
        >
          {{ value }}
        </button>
        <span v-else class="text-muted">0</span>
      </template>
      <template #cell-secondary_review="{ row, value }">
        <button
          v-if="(value as number) > 0"
          class="hover:underline"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit, status_key: 'secondary_reviewer' })"
        >
          {{ value }}
        </button>
        <span v-else class="text-muted">0</span>
      </template>
      <template #cell-approved="{ row, value }">
        <button
          v-if="(value as number) > 0"
          class="font-medium text-success hover:underline"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit, status_key: 'approved' })"
        >
          {{ value }}
        </button>
        <span v-else class="text-muted">0</span>
      </template>
      <template #cell-returned="{ value }">
        <span :class="(value as number) > 0 ? 'font-medium text-warning' : 'text-muted'">{{ value }}</span>
      </template>
    </DataTable>
  </div>
</template>
