<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { ActivityRow } from '@/types/admin'

const props = defineProps<{ activity: ActivityRow[] }>()
const router = useRouter()

function open(row: ActivityRow) {
  router.push({ name: 'project-details', params: { name: row.project_id } })
}

function relativeTime(value: string) {
  const diffMs = Date.now() - new Date(value).getTime()
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.round(diffHr / 24)
  if (diffDay === 1) return 'Yesterday'
  if (diffDay < 30) return `${diffDay}d ago`
  return new Date(value).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

function actorLabel(email: string) {
  return email === 'Administrator' ? 'Administrator' : email.split('@')[0].replace(/[._]/g, ' ')
}

const entries = computed(() => props.activity.slice(0, 10))
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <h3 class="mb-1 text-base font-semibold text-charcoal">Recent Activity</h3>
    <p class="mb-4 text-sm text-muted">The latest status changes across every project.</p>

    <EmptyState v-if="!entries.length" icon="activity" title="No recent status changes" />
    <ol v-else class="space-y-0">
      <li v-for="(row, i) in entries" :key="i" class="flex gap-3">
        <div class="flex flex-col items-center">
          <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
          <span v-if="i < entries.length - 1" class="w-px flex-1 bg-line" />
        </div>
        <button class="min-w-0 flex-1 pb-5 text-left" @click="open(row)">
          <p class="truncate text-sm font-medium text-charcoal">
            {{ row.student_names || row.project_title || row.project_id }}
          </p>
          <div class="mt-1 flex flex-wrap items-center gap-1.5">
            <span class="text-xs text-muted">{{ row.programme }}</span>
            <span class="text-xs text-muted">·</span>
            <StatusBadge :status="row.to_status" />
          </div>
          <p class="mt-1 text-xs text-muted">{{ actorLabel(row.performed_by) }} · {{ relativeTime(row.date) }}</p>
        </button>
      </li>
    </ol>
  </div>
</template>
