<script setup lang="ts">
import { computed } from 'vue'
import { AxisChart } from 'frappe-ui'

interface ChartConfig {
  data: Record<string, unknown>[]
  title: string
  xAxis: { key: string; type: 'category' | 'time' | 'value' }
  yAxis: Record<string, unknown>
  series: { name: string; type: 'bar' | 'line' | 'area'; color?: string }[]
}

const STATUS_SHORT_LABELS: Record<string, string> = {
  student_action: 'Student Action',
  mentor_approval: 'Mentor Approval',
  mentor_correction: 'Mentor Correction',
  primary_reviewer: 'Primary Reviewer',
  secondary_reviewer: 'Secondary Reviewer',
  reviewer_feedback: 'Reviewer Feedback',
  reviewer_correction: 'Reviewer Correction',
  provisional: 'Provisional',
  final_approval: 'Final Approval',
  approved: 'Approved',
}

const props = defineProps<{ statusCounts: Record<string, number> }>()

const config = computed<ChartConfig>(() => ({
  data: Object.entries(STATUS_SHORT_LABELS).map(([key, label]) => ({
    status: label,
    count: props.statusCounts[key] || 0,
  })),
  title: '',
  xAxis: { key: 'status', type: 'category' },
  // `title` must be a real string, not omitted — frappe-ui's chart options
  // build the axis label as `↑ ${yAxis.title}` with no fallback, so an
  // empty {} here rendered the literal text "↑ undefined" on the chart.
  yAxis: { title: '' },
  series: [{ name: 'count', type: 'bar', color: '#0f172a' }],
}))
</script>

<template>
  <div class="h-64">
    <AxisChart :config="config" />
  </div>
</template>
