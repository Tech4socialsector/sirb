<script setup lang="ts">
import { Avatar } from 'frappe-ui'
import EmptyState from '@/components/common/EmptyState.vue'
import type { ProjectStudent } from '@/types/project'

defineProps<{ students: ProjectStudent[] }>()
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">Student Information</h3>
    <EmptyState v-if="!students.length" icon="user" title="No students assigned" />
    <ul v-else class="space-y-3">
      <li v-for="s in students" :key="s.student_id" class="flex items-center gap-3">
        <Avatar :label="s.full_name" size="md" />
        <div class="min-w-0">
          <p class="truncate text-sm font-medium text-gray-900">{{ s.full_name }}</p>
          <p class="truncate text-xs text-gray-500">{{ s.user_email }} · {{ s.student_id }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>
