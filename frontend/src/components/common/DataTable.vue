<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import EmptyState from './EmptyState.vue'
import ErrorState from './ErrorState.vue'
import Pagination from './Pagination.vue'
import { ApiError } from '@/services/api'

export interface DataTableColumn {
  key: string
  label: string
  align?: 'left' | 'right' | 'center'
  sortable?: boolean
  /** Dot-path into the row, e.g. "student.name" — defaults to `key`. */
  path?: string
}

const props = withDefaults(
  defineProps<{
    columns: DataTableColumn[]
    rows: Record<string, unknown>[]
    rowKey?: string
    loading?: boolean
    error?: ApiError | null
    emptyTitle?: string
    emptyDescription?: string
    pageSize?: number
    clickableRows?: boolean
  }>(),
  {
    rowKey: 'name',
    loading: false,
    error: null,
    emptyTitle: 'No records found',
    emptyDescription: undefined,
    pageSize: 10,
    clickableRows: false,
  },
)

const emit = defineEmits<{ 'row-click': [Record<string, unknown>]; retry: [] }>()

const page = ref(1)
const pageSize = ref(props.pageSize)
const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')

// Reset to page 1 whenever the underlying row set changes (a new
// search/filter was applied) so the user isn't stranded on a page that no
// longer exists.
watch(
  () => props.rows,
  () => (page.value = 1),
)

function getValue(row: Record<string, unknown>, path: string) {
  return path.split('.').reduce<unknown>((acc, key) => (acc as Record<string, unknown> | undefined)?.[key], row)
}

function toggleSort(col: DataTableColumn) {
  if (!col.sortable) return
  if (sortKey.value === (col.path || col.key)) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = col.path || col.key
    sortDir.value = 'asc'
  }
}

const sortedRows = computed(() => {
  if (!sortKey.value) return props.rows
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  return [...props.rows].sort((a, b) => {
    const av = getValue(a, key)
    const bv = getValue(b, key)
    if (av == null && bv == null) return 0
    if (av == null) return -1 * dir
    if (bv == null) return 1 * dir
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
    return String(av).localeCompare(String(bv)) * dir
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return sortedRows.value.slice(start, start + pageSize.value)
})

function alignClass(align?: string) {
  if (align === 'right') return 'text-right'
  if (align === 'center') return 'text-center'
  return 'text-left'
}
</script>

<template>
  <div>
    <ErrorState v-if="error" :error="error" @retry="emit('retry')" />
    <template v-else>
      <!-- Empty / loading render outside the table so they never inherit its min-width. -->
      <div v-if="loading" class="rounded-lg border border-line bg-paper px-3 py-4">
        <div class="animate-pulse space-y-3">
          <div v-for="i in 5" :key="i" class="h-4 rounded bg-canvas" />
        </div>
      </div>
      <div v-else-if="!pagedRows.length" class="rounded-lg border border-line bg-paper px-3 py-2">
        <EmptyState icon="inbox" :title="emptyTitle" :description="emptyDescription" />
      </div>
      <template v-else>
        <!-- Phones: one card per row, each column as a label / value pair. -->
        <ul class="divide-y divide-line overflow-hidden rounded-lg border border-line bg-paper sm:hidden">
          <li
            v-for="row in pagedRows"
            :key="String(getValue(row, rowKey))"
            class="space-y-2 px-3 py-3 text-sm"
            :class="clickableRows ? 'cursor-pointer active:bg-canvas' : ''"
            @click="clickableRows && emit('row-click', row)"
          >
            <template v-for="col in columns" :key="col.key">
              <div v-if="col.label" class="flex items-start justify-between gap-3">
                <span class="shrink-0 pt-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted">{{ col.label }}</span>
                <div class="min-w-0 break-words text-right">
                  <slot :name="`cell-${col.key}`" :row="row" :value="getValue(row, col.path || col.key)">
                    {{ getValue(row, col.path || col.key) ?? '—' }}
                  </slot>
                </div>
              </div>
              <!-- Unlabelled columns (row actions) sit at the bottom of the card. -->
              <div v-else class="flex justify-end">
                <slot :name="`cell-${col.key}`" :row="row" :value="getValue(row, col.path || col.key)" />
              </div>
            </template>
          </li>
        </ul>

        <div class="hidden overflow-x-auto rounded-lg border border-line sm:block">
          <table class="w-full min-w-[640px] text-left text-sm">
            <thead class="bg-canvas">
              <tr>
                <th
                  v-for="col in columns"
                  :key="col.key"
                  class="whitespace-nowrap px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted"
                  :class="[alignClass(col.align), col.sortable ? 'cursor-pointer select-none hover:text-charcoal' : '']"
                  @click="toggleSort(col)"
                >
                  <span class="inline-flex items-center gap-1">
                    {{ col.label }}
                    <span v-if="col.sortable && sortKey === (col.path || col.key)" class="text-primary">
                      {{ sortDir === 'asc' ? '↑' : '↓' }}
                    </span>
                  </span>
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-line bg-paper">
              <tr
                v-for="row in pagedRows"
                :key="String(getValue(row, rowKey))"
                class="transition-colors"
                :class="clickableRows ? 'cursor-pointer hover:bg-canvas' : ''"
                @click="clickableRows && emit('row-click', row)"
              >
                <td v-for="col in columns" :key="col.key" class="whitespace-nowrap px-3 py-2.5" :class="alignClass(col.align)">
                  <slot :name="`cell-${col.key}`" :row="row" :value="getValue(row, col.path || col.key)">
                    {{ getValue(row, col.path || col.key) ?? '—' }}
                  </slot>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div v-if="!loading && rows.length" class="mt-3">
        <Pagination v-model:page="page" v-model:page-size="pageSize" :total="rows.length" />
      </div>
    </template>
  </div>
</template>
