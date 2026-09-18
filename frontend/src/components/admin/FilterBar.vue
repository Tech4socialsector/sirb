<script setup lang="ts">
import { reactive, watch } from 'vue'
import { Autocomplete, Button, FormControl } from 'frappe-ui'
import type { DashboardFilters, FilterOptions } from '@/types/admin'

const props = defineProps<{ options: FilterOptions }>()
const emit = defineEmits<{ apply: [DashboardFilters] }>()

const local = reactive<DashboardFilters>({})

function toOptions(items: { name: string; full_name?: string; ao_name?: string }[]) {
  return items.map((i) => ({ label: i.full_name || i.ao_name || i.name, value: i.name }))
}

const statusOptions = () => [
  { label: 'All statuses', value: '' },
  ...props.options.statuses.map((s) => ({ label: s, value: s })),
]

function apply() {
  const filters: DashboardFilters = {}
  if (local.irb_unit?.length) filters.irb_unit = local.irb_unit
  if (local.academic_year?.length) filters.academic_year = local.academic_year
  if (local.irb_cycle?.length) filters.irb_cycle = local.irb_cycle
  if (local.faculty_mentor?.length) filters.faculty_mentor = local.faculty_mentor
  if (local.primary_reviewer?.length) filters.primary_reviewer = local.primary_reviewer
  if (local.secondary_reviewer?.length) filters.secondary_reviewer = local.secondary_reviewer
  if (local.status) filters.status = local.status
  if (local.from_date) filters.from_date = local.from_date
  if (local.to_date) filters.to_date = local.to_date
  emit('apply', filters)
}

function clear() {
  Object.keys(local).forEach((k) => delete (local as Record<string, unknown>)[k])
  emit('apply', {})
}

watch(local, apply, { deep: false })
</script>

<template>
  <div class="mb-5 flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
    <div class="w-48">
      <Autocomplete
        placeholder="Programme / Course"
        :options="toOptions(options.programmes.map((p) => ({ name: p.name, ao_name: p.ao_name })))"
        :model-value="local.irb_unit?.[0]"
        @update:model-value="(v: { value: string } | undefined) => (local.irb_unit = v ? [v.value] : undefined)"
      />
    </div>
    <div class="w-40">
      <FormControl
        type="select"
        placeholder="Academic Year"
        :options="[{ label: 'All years', value: '' }, ...options.academic_years.map((y) => ({ label: y, value: y }))]"
        :model-value="local.academic_year?.[0] || ''"
        @update:model-value="(v: string) => (local.academic_year = v ? [v] : undefined)"
      />
    </div>
    <div class="w-40">
      <FormControl
        type="select"
        placeholder="Batch / Cycle"
        :options="[{ label: 'All cycles', value: '' }, ...options.cycles.map((c) => ({ label: c, value: c }))]"
        :model-value="local.irb_cycle?.[0] || ''"
        @update:model-value="(v: string) => (local.irb_cycle = v ? [v] : undefined)"
      />
    </div>
    <div class="w-56">
      <FormControl
        type="select"
        placeholder="Status"
        :options="statusOptions()"
        :model-value="local.status || ''"
        @update:model-value="(v: string) => (local.status = v || undefined)"
      />
    </div>
    <div class="w-40">
      <FormControl
        type="date"
        placeholder="From"
        :model-value="local.from_date"
        @update:model-value="(v: string) => (local.from_date = v || undefined)"
      />
    </div>
    <div class="w-40">
      <FormControl
        type="date"
        placeholder="To"
        :model-value="local.to_date"
        @update:model-value="(v: string) => (local.to_date = v || undefined)"
      />
    </div>
    <Button variant="outline" @click="clear">Clear filters</Button>
  </div>
</template>
