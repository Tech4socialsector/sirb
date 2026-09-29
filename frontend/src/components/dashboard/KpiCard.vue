<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import type { RouteLocationRaw } from 'vue-router'

const props = withDefaults(
  defineProps<{
    label: string
    value: number | string
    icon: string
    /** Supporting line under the number — real derived data only, e.g.
     * "+8 this month" or "6 need action". Omit rather than invent one. */
    support?: string
    tone?: 'default' | 'warning' | 'success' | 'info'
    to?: RouteLocationRaw
    /** Set when the card is clickable via @click rather than `to` — adds
     * the same hover affordance so it doesn't look inert. */
    clickable?: boolean
    /** Label for the small action link at the bottom, e.g. "View Projects". */
    actionLabel?: string
  }>(),
  { tone: 'default', clickable: false },
)

const toneClasses: Record<string, string> = {
  default: 'bg-primary/5 text-primary',
  warning: 'bg-amber-50 text-warning',
  success: 'bg-emerald-50 text-success',
  info: 'bg-blue-50 text-info',
}

const isInteractive = computed(() => Boolean(props.to) || props.clickable)
</script>

<template>
  <component
    :is="to ? 'RouterLink' : 'div'"
    :to="to"
    class="flex flex-col gap-4 rounded-xl border border-line bg-paper p-5 shadow-card transition-colors"
    :class="isInteractive ? 'cursor-pointer hover:border-primary' : ''"
  >
    <div class="flex items-center justify-between">
      <p class="text-sm font-medium text-muted">{{ label }}</p>
      <span class="flex h-9 w-9 items-center justify-center rounded-lg" :class="toneClasses[tone]">
        <FeatherIcon :name="icon" class="h-4.5 w-4.5" />
      </span>
    </div>
    <div>
      <p class="text-3xl font-semibold leading-none text-charcoal">{{ value }}</p>
      <p v-if="support" class="mt-2 text-sm text-muted">{{ support }}</p>
    </div>
    <p v-if="actionLabel && isInteractive" class="flex items-center gap-1 text-sm font-medium text-primary">
      {{ actionLabel }}
      <FeatherIcon name="arrow-right" class="h-3.5 w-3.5" />
    </p>
  </component>
</template>
