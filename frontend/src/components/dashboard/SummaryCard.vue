<script setup lang="ts">
import { FeatherIcon } from 'frappe-ui'

withDefaults(
  defineProps<{
    label: string
    value: number | string
    icon?: string
    to?: string
    tone?: 'default' | 'warning' | 'success'
  }>(),
  { icon: 'file-text', tone: 'default' },
)

const toneClasses: Record<string, string> = {
  default: 'bg-canvas text-muted',
  warning: 'bg-amber-50 text-warning',
  success: 'bg-emerald-50 text-success',
}
</script>

<template>
  <component
    :is="to ? 'RouterLink' : 'button'"
    :to="to"
    class="flex w-full items-start gap-3 rounded-lg border border-line bg-paper p-4 text-left shadow-card transition-colors hover:border-primary"
  >
    <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" :class="toneClasses[tone]">
      <FeatherIcon :name="icon" class="h-5 w-5" />
    </div>
    <div class="min-w-0">
      <p class="text-2xl font-semibold leading-tight text-charcoal">{{ value }}</p>
      <p class="mt-0.5 text-xs font-medium leading-snug text-muted">{{ label }}</p>
    </div>
  </component>
</template>
