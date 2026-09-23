<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, Badge } from 'frappe-ui'
import EmptyState from '@/components/common/EmptyState.vue'
import { useAuth } from '@/composables/useAuth'
import type { ProjectStudent } from '@/types/project'

const props = defineProps<{ students: ProjectStudent[] }>()

const { currentUser } = useAuth()

const isGroup = computed(() => props.students.length > 1)
</script>

<template>
  <div class="rounded-lg border border-line bg-paper p-5">
    <div class="mb-4 flex items-center justify-between gap-2">
      <h3 class="text-sm font-semibold text-charcoal">{{ isGroup ? 'Team Members' : 'Student Information' }}</h3>
      <Badge v-if="isGroup" theme="blue" variant="subtle" size="sm">Group · {{ students.length }}</Badge>
    </div>
    <EmptyState v-if="!students.length" icon="user" title="No students assigned" />
    <ul v-else class="space-y-3">
      <li v-for="s in students" :key="s.user_email" class="flex items-center gap-3">
        <Avatar :label="s.full_name" size="md" />
        <div class="min-w-0">
          <p class="flex items-center gap-2 truncate text-sm font-medium text-charcoal">
            {{ s.full_name }}
            <Badge v-if="s.user_email === currentUser?.user" theme="gray" variant="subtle" size="sm">You</Badge>
          </p>
          <p class="truncate text-xs text-muted">{{ s.user_email }} · {{ s.student_id }}</p>
        </div>
      </li>
    </ul>
  </div>
</template>
