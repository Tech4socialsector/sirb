<script setup lang="ts">
import { computed } from 'vue'
import { Avatar } from 'frappe-ui'
import type { RoleWorkload } from '@/types/admin'

const props = defineProps<{ workload: RoleWorkload }>()
const emit = defineEmits<{ drill: [{ role: string; faculty: string }] }>()

const sections: { title: string; role: 'mentor' | 'primary_reviewer' | 'secondary_reviewer' }[] = [
  { title: 'Mentors', role: 'mentor' },
  { title: 'Primary Reviewers', role: 'primary_reviewer' },
  { title: 'Secondary Reviewers', role: 'secondary_reviewer' },
]

function rowsFor(role: string) {
  if (role === 'mentor') return props.workload.mentors
  if (role === 'primary_reviewer') return props.workload.primary_reviewers
  return props.workload.secondary_reviewers
}

function maxFor(role: string) {
  return Math.max(1, ...rowsFor(role).map((r) => r.pending_count))
}

const totalPending = computed(() =>
  [...props.workload.mentors, ...props.workload.primary_reviewers, ...props.workload.secondary_reviewers].reduce(
    (acc, r) => acc + r.pending_count,
    0,
  ),
)
</script>

<template>
  <div class="rounded-xl border border-line bg-paper p-6 shadow-card">
    <div class="mb-5">
      <h3 class="text-base font-semibold text-charcoal">Mentor &amp; Reviewer Workload</h3>
      <p class="text-sm text-muted">{{ totalPending }} pending review{{ totalPending === 1 ? '' : 's' }} across everyone right now.</p>
    </div>
    <div class="grid gap-6 md:grid-cols-3">
      <div v-for="section in sections" :key="section.role">
        <p class="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">{{ section.title }}</p>
        <p v-if="!rowsFor(section.role).length" class="text-sm text-muted">Nobody has pending work here.</p>
        <div v-else class="space-y-3">
          <button
            v-for="row in rowsFor(section.role)"
            :key="row.faculty_id"
            class="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-canvas"
            @click="emit('drill', { role: section.role, faculty: row.faculty_id })"
          >
            <Avatar :label="row.faculty_name || row.faculty_id" size="md" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-charcoal">{{ row.faculty_name || row.faculty_id }}</p>
              <div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-canvas">
                <div
                  class="h-full rounded-full bg-primary"
                  :style="{ width: `${(row.pending_count / maxFor(section.role)) * 100}%` }"
                />
              </div>
            </div>
            <span class="shrink-0 text-sm font-semibold text-charcoal">{{ row.pending_count }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
