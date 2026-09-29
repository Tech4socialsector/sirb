<script setup lang="ts">
import { computed, ref } from 'vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import type { ProgrammeMatrixRow } from '@/types/admin'

const props = defineProps<{ rows: ProgrammeMatrixRow[] }>()
const emit = defineEmits<{ drill: [{ irb_unit?: string; status_keys?: string[]; label?: string }] }>()

const search = ref('')

// Every status belongs to exactly one column, so the columns always add up
// to Total. Stages are grouped the same way as the Project Approval
// Pipeline above. There is no "Rejected" status in this workflow — only
// "returned for correction" — so no rejected column.
const STAGES: { key: string; label: string; statuses: string[]; tone?: string }[] = [
  { key: 'student_action', label: 'Student Action', statuses: ['student_action'] },
  { key: 'returned', label: 'Returned', statuses: ['mentor_correction', 'reviewer_correction'], tone: 'text-warning' },
  { key: 'mentor_review', label: 'Mentor Review', statuses: ['mentor_approval'] },
  { key: 'primary_review', label: 'Primary Review', statuses: ['primary_reviewer', 'reviewer_feedback'] },
  { key: 'secondary_review', label: 'Secondary Review', statuses: ['secondary_reviewer'] },
  { key: 'final_approval', label: 'Final Approval', statuses: ['final_approval', 'provisional'] },
  { key: 'approved', label: 'Approved', statuses: ['approved'], tone: 'text-success' },
]

const summarized = computed(() =>
  props.rows.map((r) => ({
    irb_unit: r.irb_unit,
    programme: r.programme || r.irb_unit,
    total: r.total,
    ...Object.fromEntries(STAGES.map((st) => [st.key, st.statuses.reduce((a, k) => a + (r.statuses[k] || 0), 0)])),
  })),
)

const filteredRows = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return summarized.value
  return summarized.value.filter((r) => r.programme.toLowerCase().includes(term))
})

type SummarizedRow = (typeof summarized)['value'][number]
function asRow(row: Record<string, unknown>) {
  return row as unknown as SummarizedRow
}

const columns: DataTableColumn[] = [
  { key: 'programme', label: 'Programme', sortable: true },
  { key: 'total', label: 'Total', align: 'right', sortable: true },
  ...STAGES.map((st) => ({ key: st.key, label: st.label, align: 'right' as const, sortable: true })),
]
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 class="text-base font-semibold text-charcoal">Programme Analytics</h3>
        <p class="text-sm text-muted">Where each programme's projects stand right now. Click a number to see its projects.</p>
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
        <span class="font-medium text-charcoal">{{ asRow(row).programme }}</span>
      </template>
      <template #cell-total="{ row, value }">
        <button class="font-semibold text-primary hover:underline" @click="emit('drill', { irb_unit: asRow(row).irb_unit })">
          {{ value }}
        </button>
      </template>
      <template v-for="st in STAGES" :key="st.key" #[`cell-${st.key}`]="{ row, value }">
        <button
          v-if="(value as number) > 0"
          class="hover:underline"
          :class="st.tone ? `font-medium ${st.tone}` : ''"
          @click="emit('drill', { irb_unit: asRow(row).irb_unit, status_keys: st.statuses, label: st.label })"
        >
          {{ value }}
        </button>
        <span v-else class="text-muted">0</span>
      </template>
    </DataTable>
  </div>
</template>
