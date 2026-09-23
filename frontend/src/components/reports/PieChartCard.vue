<script setup lang="ts">
import { computed } from 'vue'
import { ECharts } from 'frappe-ui'
import type { EChartsOption } from 'echarts'

export interface PieSlice {
  key: string
  label: string
  value: number
}

// Fixed categorical order (validated for adjacent-pair colour-blind
// separation). Colour is assigned by the slice's position in `slices`, not
// by its rank among non-zero slices, so a category keeps its colour when
// another one drops to 0.
const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
const TEXT = '#334155'
const MUTED = '#94a3b8'

const props = defineProps<{ title: string; subtitle?: string; slices: PieSlice[] }>()
const emit = defineEmits<{ select: [key: string] }>()

const colored = computed(() => props.slices.map((s, i) => ({ ...s, color: PALETTE[i % PALETTE.length] })))
const total = computed(() => props.slices.reduce((a, s) => a + s.value, 0))

function pct(value: number) {
  return total.value ? Math.round((value / total.value) * 100) : 0
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
}

const options = computed<EChartsOption>(() => ({
  animationDuration: 500,
  textStyle: { fontFamily: 'Poppins, ui-sans-serif, system-ui, sans-serif' },
  tooltip: {
    trigger: 'item',
    confine: true,
    formatter: (params) => {
      const p = params as unknown as { name: string; value: number; color: string }
      return (
        `<div style="display:flex;align-items:center;gap:8px">` +
        `<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${p.color}"></span>` +
        `<span>${escapeHtml(p.name)}</span><b style="margin-left:12px">${p.value} (${pct(p.value)}%)</b></div>`
      )
    },
  },
  series: [
    {
      type: 'pie',
      radius: '72%',
      center: ['50%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#ffffff', borderWidth: 2 },
      label: { show: true, formatter: '{c}', color: TEXT, fontSize: 13, fontWeight: 500 },
      labelLine: { show: true, length: 8, length2: 10, lineStyle: { color: MUTED } },
      emphasis: { scaleSize: 6 },
      // Zero-value slices are dropped from the pie itself (they'd render
      // as a stray "0" label at a single point) but stay in the legend.
      data: colored.value
        .filter((s) => s.value > 0)
        .map((s) => ({ name: s.label, value: s.value, key: s.key, itemStyle: { color: s.color } })),
    },
  ],
}))

// frappe-ui's ECharts binds this handler once on mount, so it must not
// close over reactive state — it only reads the clicked item's own key.
const events = { click: (p: { data?: { key?: string } }) => p.data?.key && emit('select', p.data.key) }
</script>

<template>
  <div class="flex h-full flex-col rounded-xl border border-line bg-paper p-6 shadow-card">
    <h3 class="text-base font-semibold text-charcoal">{{ title }}</h3>
    <p v-if="subtitle" class="text-sm text-muted">{{ subtitle }}</p>
    <div v-if="total > 0" class="h-64">
      <ECharts :options="options" :events="events" class="h-full w-full cursor-pointer" />
    </div>
    <div v-else class="flex h-64 items-center justify-center text-sm text-muted">No data for this selection.</div>
    <div class="mt-auto flex flex-wrap justify-center gap-x-4 gap-y-2 pt-3">
      <button
        v-for="s in colored"
        :key="s.key"
        type="button"
        class="inline-flex items-center gap-1.5 rounded text-xs text-charcoal transition-opacity disabled:cursor-default disabled:opacity-50 [&:not(:disabled)]:hover:underline"
        :disabled="s.value === 0"
        @click="emit('select', s.key)"
      >
        <span class="h-2.5 w-2.5 shrink-0 rounded-sm" :style="{ backgroundColor: s.color }" />
        {{ s.label }}
        <span class="text-muted">{{ s.value }} ({{ pct(s.value) }}%)</span>
      </button>
    </div>
  </div>
</template>
