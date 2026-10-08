<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

// Same fills as the Desk "IRB Projects" workspace number cards.
const TONES = {
  pending: 'bg-[#F9E795] hover:ring-[#d9c35a]',
  unapproved: 'bg-[#D08EA6] hover:ring-[#a8607a]',
  approved: 'bg-[#88BCB8] hover:ring-[#5a938f]',
} as const

defineProps<{
  label: string
  value: number
  tone: keyof typeof TONES
  to: RouteLocationRaw
}>()
</script>

<template>
  <RouterLink
    :to="to"
    class="flex min-h-[5.5rem] flex-col justify-between gap-3 rounded-lg p-4 shadow-card ring-2 ring-transparent transition-shadow focus:outline-none focus-visible:ring-charcoal"
    :class="TONES[tone]"
    :aria-label="`${label}: ${value}`"
  >
    <p class="text-xs font-medium uppercase tracking-wide text-charcoal/80">{{ label }}</p>
    <p class="text-2xl font-semibold leading-none text-charcoal">{{ value }}</p>
  </RouterLink>
</template>
