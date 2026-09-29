<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog } from 'frappe-ui'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import RunStatusBadge from './RunStatusBadge.vue'
import { fetchRun } from '@/services/alerts'
import { ApiError } from '@/services/api'
import type { FilterOptions } from '@/types/admin'
import type { AlertRunDetail, AlertRunRecipient } from '@/types/alerts'
import { describeFilters } from '@/utils/alertFilters'
import { formatServerDateTime } from '@/utils/serverTime'

const props = defineProps<{ modelValue: boolean; runName: string | null; options: FilterOptions | null }>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const run = ref<AlertRunDetail | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const statusFilter = ref<'all' | AlertRunRecipient['status']>('all')
let seq = 0

async function load() {
  if (!props.runName) return
  const mine = ++seq
  loading.value = true
  error.value = null
  try {
    const r = await fetchRun(props.runName)
    if (mine === seq) run.value = r
  } catch (e) {
    if (mine === seq) error.value = e instanceof ApiError ? e : new ApiError('Could not load this run.', 'server')
  } finally {
    if (mine === seq) loading.value = false
  }
}

watch(
  () => [props.modelValue, props.runName] as const,
  ([open]) => {
    if (!open) return
    run.value = null
    statusFilter.value = 'all'
    load()
  },
  { immediate: true },
)

const rows = computed(() => {
  const all = run.value?.recipients ?? []
  return statusFilter.value === 'all' ? all : all.filter((r) => r.status === statusFilter.value)
})
const counts = computed(() => {
  const c = { all: 0, Queued: 0, Skipped: 0, Failed: 0 }
  for (const r of run.value?.recipients ?? []) {
    c.all++
    c[r.status]++
  }
  return c
})
const CHIPS = [
  { value: 'all', label: 'All' },
  { value: 'Queued', label: 'Queued' },
  { value: 'Skipped', label: 'Skipped' },
  { value: 'Failed', label: 'Failed' },
] as const

const columns: DataTableColumn[] = [
  { key: 'student_name', label: 'Student', sortable: true },
  { key: 'irb_project', label: 'Project', sortable: true },
  { key: 'status', label: 'Result', sortable: true },
  { key: 'reason', label: 'Note' },
]
const STATUS_CLASS: Record<AlertRunRecipient['status'], string> = {
  Queued: 'bg-green-50 text-success',
  Skipped: 'bg-canvas text-muted',
  Failed: 'bg-red-50 text-danger',
}
</script>

<template>
  <Dialog :model-value="modelValue" :options="{ title: run?.alert_name || 'Alert run', size: '4xl' }" @update:model-value="(v: boolean) => emit('update:modelValue', v)">
    <template #body-content>
      <LoadingState v-if="loading && !run" label="Loading run…" />
      <ErrorState v-else-if="error" :error="error" @retry="load" />
      <div v-else-if="run" class="space-y-4">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <RunStatusBadge :status="run.status" />
          <span>{{ run.trigger }} · {{ formatServerDateTime(run.creation) }}</span>
          <span v-if="run.triggered_by_name">by {{ run.triggered_by_name }}</span>
          <span>Template: <span class="text-charcoal">{{ run.email_template }}</span></span>
        </div>
        <p class="text-sm text-muted">Filters: <span class="text-charcoal">{{ describeFilters(run.filters, options).join(' · ') }}</span></p>
        <p v-if="run.deadline_label" class="text-sm text-muted">Reminded about: <span class="text-charcoal">{{ run.deadline_label }}</span></p>

        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-lg border border-line p-3">
            <p class="text-xs text-muted">Matched</p>
            <p class="text-lg font-semibold text-charcoal">{{ run.total_recipients }}</p>
          </div>
          <div class="rounded-lg border border-line p-3">
            <p class="text-xs text-muted">Queued for delivery</p>
            <p class="text-lg font-semibold text-success">{{ run.sent_count }}</p>
          </div>
          <div class="rounded-lg border border-line p-3">
            <p class="text-xs text-muted">Skipped</p>
            <p class="text-lg font-semibold text-charcoal">{{ run.skipped_count }}</p>
          </div>
          <div class="rounded-lg border border-line p-3">
            <p class="text-xs text-muted">Failed</p>
            <p class="text-lg font-semibold" :class="run.failed_count ? 'text-danger' : 'text-charcoal'">{{ run.failed_count }}</p>
          </div>
        </div>

        <p v-if="run.error" class="rounded-md bg-red-50 px-3 py-2 text-sm text-danger">{{ run.error }}</p>
        <p v-else-if="run.status === 'Queued' || run.status === 'Running'" class="text-sm text-muted">
          This run is still in progress. The recipient list appears when it finishes.
        </p>

        <template v-if="run.recipients.length">
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="chip in CHIPS"
              :key="chip.value"
              type="button"
              class="rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors"
              :class="statusFilter === chip.value ? 'border-primary bg-primary text-white' : 'border-line text-muted hover:text-charcoal'"
              @click="statusFilter = chip.value"
            >
              {{ chip.label }} ({{ counts[chip.value] }})
            </button>
          </div>
          <DataTable :columns="columns" :rows="rows as unknown as Record<string, unknown>[]" row-key="idx" empty-title="No recipients in this group">
            <template #cell-student_name="{ row }">
              <p class="font-medium text-charcoal">{{ (row as unknown as AlertRunRecipient).student_name }}</p>
              <p class="text-xs text-muted">{{ (row as unknown as AlertRunRecipient).email || 'no e-mail' }}</p>
            </template>
            <template #cell-irb_project="{ value }">
              <RouterLink :to="`/sirb/projects/${value}`" class="text-primary hover:underline" target="_blank">#{{ value }}</RouterLink>
            </template>
            <template #cell-status="{ value }">
              <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="STATUS_CLASS[value as AlertRunRecipient['status']]">{{ value }}</span>
            </template>
            <template #cell-reason="{ value }"><span class="text-xs text-muted">{{ value || '' }}</span></template>
          </DataTable>
          <p class="text-xs text-muted">
            "Queued for delivery" means the e-mail is in the site's outgoing queue; the queue sends it within a few minutes and retries on failures.
          </p>
        </template>
      </div>
    </template>
  </Dialog>
</template>
