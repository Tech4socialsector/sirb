<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'

const props = withDefaults(
  defineProps<{
    total: number
    page: number
    pageSize: number
    pageSizeOptions?: number[]
  }>(),
  { pageSizeOptions: () => [10, 25, 50, 100] },
)

const emit = defineEmits<{ 'update:page': [number]; 'update:pageSize': [number] }>()

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const rangeStart = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const rangeEnd = computed(() => Math.min(props.total, props.page * props.pageSize))

// Compact page list: first, last, current ± 1, with "…" gaps — avoids
// rendering a button for every page when there are dozens of them.
const pageItems = computed<(number | '…')[]>(() => {
  const count = pageCount.value
  const current = props.page
  if (count <= 7) return Array.from({ length: count }, (_, i) => i + 1)
  const items = new Set([1, count, current, current - 1, current + 1])
  const sorted = [...items].filter((p) => p >= 1 && p <= count).sort((a, b) => a - b)
  const out: (number | '…')[] = []
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) out.push('…')
    out.push(sorted[i])
  }
  return out
})

function goTo(p: number) {
  if (p >= 1 && p <= pageCount.value) emit('update:page', p)
}
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 text-sm">
    <div class="flex items-center gap-2 text-muted">
      <span>Showing {{ rangeStart }}–{{ rangeEnd }} of {{ total }}</span>
      <select
        class="rounded-md border border-line bg-canvas px-2 py-1 text-charcoal focus:border-primary focus:outline-none"
        :value="pageSize"
        @change="emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
      >
        <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }} / page</option>
      </select>
    </div>

    <div v-if="pageCount > 1" class="flex items-center gap-1">
      <button
        class="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-canvas hover:text-charcoal disabled:pointer-events-none disabled:opacity-40"
        :disabled="page <= 1"
        aria-label="Previous page"
        @click="goTo(page - 1)"
      >
        <FeatherIcon name="chevron-left" class="h-4 w-4" />
      </button>
      <template v-for="(item, i) in pageItems" :key="i">
        <span v-if="item === '…'" class="px-1.5 text-muted">…</span>
        <button
          v-else
          class="flex h-8 w-8 items-center justify-center rounded-md text-sm font-medium transition-colors"
          :class="item === page ? 'bg-primary text-white' : 'text-charcoal hover:bg-canvas'"
          @click="goTo(item)"
        >
          {{ item }}
        </button>
      </template>
      <button
        class="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-canvas hover:text-charcoal disabled:pointer-events-none disabled:opacity-40"
        :disabled="page >= pageCount"
        aria-label="Next page"
        @click="goTo(page + 1)"
      >
        <FeatherIcon name="chevron-right" class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>
