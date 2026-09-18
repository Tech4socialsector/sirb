<script setup lang="ts">
import type { RoleWorkload } from '@/types/admin'

const props = defineProps<{ workload: RoleWorkload }>()
const emit = defineEmits<{ drill: [{ role: string; faculty: string }] }>()

const sections: { title: string; role: 'mentor' | 'primary_reviewer' | 'secondary_reviewer' }[] = [
  { title: 'Faculty Mentors', role: 'mentor' },
  { title: 'Primary Reviewers', role: 'primary_reviewer' },
  { title: 'Secondary Reviewers', role: 'secondary_reviewer' },
]

function rowsFor(role: string) {
  if (role === 'mentor') return props.workload.mentors
  if (role === 'primary_reviewer') return props.workload.primary_reviewers
  return props.workload.secondary_reviewers
}
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">Workload by Role</h3>
    <div class="grid gap-6 md:grid-cols-3">
      <div v-for="section in sections" :key="section.role">
        <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{{ section.title }}</p>
        <p v-if="!rowsFor(section.role).length" class="text-sm text-gray-400">Nobody has pending work here.</p>
        <div v-else class="space-y-1">
          <button
            v-for="row in rowsFor(section.role)"
            :key="row.faculty_id"
            class="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-gray-50"
            @click="emit('drill', { role: section.role, faculty: row.faculty_id })"
          >
            <span class="truncate text-gray-700">{{ row.faculty_name || row.faculty_id }}</span>
            <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
              {{ row.pending_count }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
