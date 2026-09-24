<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Button, FormControl, MultiSelect } from 'frappe-ui'
import type { DashboardFilters, FilterOptions } from '@/types/admin'

const props = defineProps<{ options: FilterOptions }>()
const emit = defineEmits<{ apply: [DashboardFilters] }>()

type MultiKey = 'campus' | 'irb_unit' | 'academic_year' | 'irb_cycle' | 'status'
const MULTI_KEYS: MultiKey[] = ['campus', 'irb_unit', 'academic_year', 'irb_cycle', 'status']

const emptyState = () => ({
  campus: [] as string[],
  irb_unit: [] as string[],
  academic_year: [] as string[],
  irb_cycle: [] as string[],
  status: [] as string[],
  from_date: '',
  to_date: '',
})
const local = reactive(emptyState())

const campusOptions = computed(() => (props.options.campuses ?? []).map((c) => ({ label: c.ao_name || c.name, value: c.name })))

// With campuses selected, only offer the programmes inside them.
const programmeOptions = computed(() =>
  props.options.programmes
    .filter((p) => !local.campus.length || (p.campus && local.campus.includes(p.campus)))
    .map((p) => ({ label: p.ao_name || p.name, value: p.name })),
)
const yearOptions = computed(() => props.options.academic_years.map((y) => ({ label: y, value: y })))
const cycleOptions = computed(() => props.options.cycles.map((c) => ({ label: c, value: c })))
const statusOptions = computed(() => props.options.statuses.map((s) => ({ label: s, value: s })))

// Picking a campus drops selected programmes outside it, which would
// otherwise silently AND the result down to nothing.
watch(
  () => [...local.campus],
  () => {
    const allowed = new Set(programmeOptions.value.map((o) => o.value))
    const kept = local.irb_unit.filter((p) => allowed.has(p))
    if (kept.length !== local.irb_unit.length) local.irb_unit = kept
  },
)

const hasActiveFilters = computed(() => MULTI_KEYS.some((k) => local[k].length) || !!local.from_date || !!local.to_date)
const dateRangeInvalid = computed(() => !!local.from_date && !!local.to_date && local.from_date > local.to_date)

const filters = computed<DashboardFilters>(() => {
  const f: DashboardFilters = {}
  for (const k of MULTI_KEYS) if (local[k].length) f[k] = [...local[k]]
  if (!dateRangeInvalid.value) {
    if (local.from_date) f.from_date = local.from_date
    if (local.to_date) f.to_date = local.to_date
  }
  return f
})

// Emit only when the effective filters change (e.g. not on a campus change
// that leaves the same programmes), so the dashboard doesn't refetch for nothing.
watch(
  () => JSON.stringify(filters.value),
  () => emit('apply', filters.value),
)

function clear() {
  Object.assign(local, emptyState())
}
</script>

<template>
  <div class="mb-5 rounded-lg border border-line bg-paper p-4 shadow-card">
    <!-- Even grid: fields keep equal widths and wrap into tidy rows. -->
    <div class="grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] items-end gap-3">
      <div v-if="campusOptions.length" class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">Campus</label>
        <MultiSelect v-model="local.campus" :options="campusOptions" placeholder="All campuses" class="w-full" />
      </div>
      <div class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">Programme / Course</label>
        <MultiSelect
          v-model="local.irb_unit"
          :options="programmeOptions"
          placeholder="All programmes"
          empty-text="No programmes in the selected campus"
          class="w-full"
        />
      </div>
      <div class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">Academic Year</label>
        <MultiSelect v-model="local.academic_year" :options="yearOptions" placeholder="All years" empty-text="No academic years" class="w-full" />
      </div>
      <div class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">Batch / Cycle</label>
        <MultiSelect v-model="local.irb_cycle" :options="cycleOptions" placeholder="All cycles" class="w-full" />
      </div>
      <div class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">Status</label>
        <MultiSelect v-model="local.status" :options="statusOptions" placeholder="All statuses" class="w-full" />
      </div>
      <div class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">From</label>
        <FormControl type="date" class="w-full" :model-value="local.from_date" @update:model-value="(v: string) => (local.from_date = v || '')" />
      </div>
      <div class="min-w-0">
        <label class="mb-1.5 block text-xs font-medium text-muted">To</label>
        <FormControl type="date" class="w-full" :model-value="local.to_date" @update:model-value="(v: string) => (local.to_date = v || '')" />
      </div>
      <div><Button variant="outline" :disabled="!hasActiveFilters" @click="clear">Clear filters</Button></div>
    </div>
    <p v-if="dateRangeInvalid" class="mt-2 text-xs text-danger">"From" is after "To" — the date range is ignored until it's fixed.</p>
  </div>
</template>
