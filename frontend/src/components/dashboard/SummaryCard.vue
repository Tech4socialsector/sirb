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
  default: 'bg-gray-100 text-gray-600',
  warning: 'bg-amber-50 text-amber-600',
  success: 'bg-emerald-50 text-emerald-600',
}
</script>

<template>
  <component
    :is="to ? 'RouterLink' : 'button'"
    :to="to"
    class="flex w-full items-center gap-3 rounded-lg border border-gray-200 bg-white p-4 text-left transition-shadow hover:shadow-sm"
  >
    <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" :class="toneClasses[tone]">
      <FeatherIcon :name="icon" class="h-5 w-5" />
    </div>
    <div class="min-w-0">
      <p class="text-2xl font-semibold leading-tight">{{ value }}</p>
      <p class="truncate text-xs font-medium text-gray-500">{{ label }}</p>
    </div>
  </component>
</template>
