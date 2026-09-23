<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'

export interface PipelineStage {
  key: string
  label: string
  count: number
  icon: string
}

const props = defineProps<{ stages: PipelineStage[] }>()
const emit = defineEmits<{ select: [key: string] }>()

const maxCount = computed(() => Math.max(1, ...props.stages.map((s) => s.count)))
const busiest = computed(() => {
  const withWork = props.stages.filter((s) => s.count > 0)
  if (!withWork.length) return null
  return withWork.reduce((a, b) => (b.count > a.count ? b : a))
})
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-5 flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 class="text-base font-semibold text-charcoal">Project Approval Pipeline</h3>
        <p class="text-sm text-muted">Where every active project currently sits in the review process.</p>
      </div>
      <p v-if="busiest" class="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-warning">
        Busiest stage: {{ busiest.label }} ({{ busiest.count }})
      </p>
    </div>

    <div class="flex flex-col gap-3 sm:flex-row sm:items-stretch">
      <template v-for="(stage, i) in stages" :key="stage.key">
        <button
          class="flex flex-1 flex-col items-center gap-2 rounded-lg border border-line px-3 py-4 text-center transition-colors hover:border-primary hover:bg-canvas"
          @click="emit('select', stage.key)"
        >
          <span
            class="flex h-10 w-10 items-center justify-center rounded-lg"
            :class="stage.count > 0 ? 'bg-primary/10 text-primary' : 'bg-canvas text-muted'"
          >
            <FeatherIcon :name="stage.icon" class="h-5 w-5" />
          </span>
          <p class="text-2xl font-semibold text-charcoal">{{ stage.count }}</p>
          <p class="text-xs font-medium uppercase tracking-wide text-muted">{{ stage.label }}</p>
          <div class="h-1.5 w-full overflow-hidden rounded-full bg-canvas">
            <div
              class="h-full rounded-full bg-primary transition-all"
              :style="{ width: `${(stage.count / maxCount) * 100}%` }"
            />
          </div>
        </button>
        <div v-if="i < stages.length - 1" class="hidden shrink-0 items-center justify-center sm:flex">
          <FeatherIcon name="chevron-right" class="h-5 w-5 text-line" />
        </div>
      </template>
    </div>
  </div>
</template>
