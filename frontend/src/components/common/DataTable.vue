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
      <div class="overflow-x-auto rounded-lg border border-line">
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
            <tr v-if="loading">
              <td :colspan="columns.length" class="px-3 py-2">
                <div class="animate-pulse space-y-3 py-2">
                  <div v-for="i in 5" :key="i" class="h-4 rounded bg-canvas" />
                </div>
              </td>
            </tr>
            <tr v-else-if="!pagedRows.length">
              <td :colspan="columns.length" class="px-3 py-8">
                <EmptyState icon="inbox" :title="emptyTitle" :description="emptyDescription" />
              </td>
            </tr>
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

      <div v-if="!loading && rows.length" class="mt-3">
        <Pagination v-model:page="page" v-model:page-size="pageSize" :total="rows.length" />
      </div>
    </template>
  </div>
</template>
