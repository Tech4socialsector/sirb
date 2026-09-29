<script setup lang="ts">
import { computed } from 'vue'
import { AxisChart } from 'frappe-ui'

const props = defineProps<{ labels: string[]; values: number[] }>()
const emit = defineEmits<{ select: [index: number] }>()

const config = computed(() => ({
  data: props.labels.map((label, i) => ({ label, count: props.values[i] || 0 })),
  title: '',
  xAxis: { key: 'label', type: 'category' as const },
  yAxis: { title: '' },
  series: [{ name: 'count', type: 'bar' as const, color: '#0f172a' }],
}))

const hasData = computed(() => props.values.some((v) => v > 0))
</script>

<template>
  <div>
    <!-- h-[300px] matches AxisChart's own min-h-[300px]; a shorter box let
     the chart overflow under the pills below.
     AxisChart/ECharts doesn't expose a typed per-bar click handler
     through this wrapper, so the pills below (same data) are what's
     actually clickable for drill-down, not the bars themselves. -->
    <div v-if="hasData" class="h-[300px]">
      <AxisChart :config="config" />
    </div>
    <div v-else class="flex h-[300px] items-center justify-center text-sm text-muted">No data for this selection.</div>
    <div class="mt-3 flex flex-wrap gap-2">
      <button
        v-for="(label, i) in labels"
        :key="label"
        class="rounded-full border border-line px-3 py-1 text-xs font-medium text-charcoal transition-colors hover:border-primary hover:bg-canvas"
        @click="emit('select', i)"
      >
        {{ label }}: {{ values[i] || 0 }}
      </button>
    </div>
  </div>
</template>
