<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, FeatherIcon } from 'frappe-ui'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { StatusChangeEntry } from '@/types/project'

const props = withDefaults(
  defineProps<{
    history: StatusChangeEntry[]
    loading?: boolean
    /** Drop the card chrome (border/padding/heading) when embedded inside
     * another container that already provides it, e.g. the timeline drawer. */
    bare?: boolean
    /** Stack the from/to status pair vertically instead of side-by-side —
     * reads better at drawer width than two long status strings crammed
     * onto one line. */
    stacked?: boolean
  }>(),
  { loading: false, bare: false, stacked: false },
)

const entries = computed(() =>
  [...props.history].map((entry, i) => ({ ...entry, isCurrent: i === props.history.length - 1 })),
)

function userLabel(email: string) {
  return email === 'Administrator' ? 'Administrator' : email.split('@')[0].replace(/[._]/g, ' ')
}

function formatDate(value: string) {
  const date = new Date(value)
  return {
    absolute: date.toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
    relative: relativeTime(date),
  }
}

function relativeTime(date: Date) {
  const diffMs = Date.now() - date.getTime()
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  if (diffDay < 30) return `${diffDay}d ago`
  return date.toLocaleDateString(undefined, { dateStyle: 'medium' })
}
</script>

<template>
  <div :class="bare ? '' : 'rounded-lg border border-line bg-paper p-5 shadow-card'">
    <h3 v-if="!bare" class="mb-4 text-sm font-semibold text-charcoal">Approval Timeline</h3>

    <ol v-if="loading" class="space-y-4" aria-hidden="true">
      <li v-for="i in 3" :key="i" class="flex animate-pulse gap-4">
        <span class="h-6 w-6 shrink-0 rounded-full bg-canvas" />
        <div class="flex-1 space-y-2 pb-6">
          <div class="h-4 w-2/3 rounded bg-canvas" />
          <div class="h-3 w-1/3 rounded bg-canvas" />
        </div>
      </li>
    </ol>
    <EmptyState v-else-if="!history.length" icon="clock" title="No status changes yet" />
    <ol v-else class="space-y-0">
      <li v-for="(entry, i) in entries" :key="i" class="flex gap-4">
        <div class="flex flex-col items-center">
          <span
            class="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
            :class="entry.isCurrent ? 'bg-primary text-white' : 'bg-canvas text-muted'"
          >
            <FeatherIcon :name="entry.isCurrent ? 'check' : 'circle'" class="h-3 w-3" />
          </span>
          <span v-if="i < entries.length - 1" class="w-px flex-1 bg-line" />
        </div>
        <div class="min-w-0 flex-1 pb-6">
          <div v-if="stacked" class="flex flex-col items-start gap-1.5">
            <StatusBadge :status="entry.from_status" />
            <FeatherIcon name="arrow-down" class="h-3.5 w-3.5 shrink-0 text-muted" />
            <div class="flex flex-wrap items-center gap-2">
              <StatusBadge :status="entry.to_status" />
              <span
                v-if="entry.isCurrent"
                class="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-white"
              >
                Current
              </span>
            </div>
          </div>
          <div v-else class="flex flex-wrap items-center gap-x-2 gap-y-1.5">
            <StatusBadge :status="entry.from_status" />
            <FeatherIcon name="arrow-right" class="h-3.5 w-3.5 shrink-0 text-muted" />
            <StatusBadge :status="entry.to_status" />
            <span v-if="entry.isCurrent" class="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-white">
              Current
            </span>
          </div>
          <div class="mt-2.5 flex items-center gap-1.5 text-sm text-muted">
            <Avatar :label="userLabel(entry.changed_by)" size="sm" />
            <span class="font-medium text-charcoal">{{ userLabel(entry.changed_by) }}</span>
            <span>·</span>
            <span :title="formatDate(entry.date).absolute">{{ formatDate(entry.date).relative }}</span>
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>
