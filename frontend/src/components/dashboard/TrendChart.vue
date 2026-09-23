<script setup lang="ts">
import { computed } from 'vue'
import { AxisChart } from 'frappe-ui'
import type { TrendPoint } from '@/types/admin'

const props = defineProps<{ points: TrendPoint[] }>()

const config = computed(() => ({
  data: props.points,
  title: '',
  xAxis: { key: 'month', type: 'category' as const },
  yAxis: { title: '' },
  series: [{ name: 'count', type: 'area' as const, color: '#0f172a' }],
}))

const hasData = computed(() => props.points.some((p) => p.count > 0))
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <h3 class="text-base font-semibold text-charcoal">Project Trends</h3>
    <p class="mb-4 text-sm text-muted">New projects submitted per month.</p>
    <div v-if="hasData" class="h-56">
      <AxisChart :config="config" />
    </div>
    <div v-else class="flex h-56 items-center justify-center text-sm text-muted">
      No new projects in this period yet.
    </div>
  </div>
</template>
