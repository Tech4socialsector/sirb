<script setup lang="ts">
import { FeatherIcon } from 'frappe-ui'
import type { DashboardData } from '@/types/admin'

const props = defineProps<{ pendingActions: DashboardData['pending_actions'] }>()
const emit = defineEmits<{ drill: [group: string] }>()

const items = [
  { label: 'Student Action Required', group: 'student_action_required', icon: 'user' },
  { label: 'Faculty Mentor Action Required', group: 'mentor_action_required', icon: 'user-check' },
  { label: 'Reviewer Action Required', group: 'reviewer_action_required', icon: 'eye' },
  { label: 'Final Approval Required', group: 'final_approval_required', icon: 'flag' },
]
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">Pending Actions</h3>
    <div class="divide-y divide-gray-100">
      <button
        v-for="item in items"
        :key="item.group"
        class="flex w-full items-center gap-3 py-2.5 text-left hover:bg-gray-50"
        @click="emit('drill', item.group)"
      >
        <FeatherIcon :name="item.icon" class="h-4 w-4 text-gray-400" />
        <span class="flex-1 text-sm text-gray-700">{{ item.label }}</span>
        <span
          class="text-sm font-semibold"
          :class="props.pendingActions[item.group] ? 'text-amber-600' : 'text-gray-400'"
        >
          {{ props.pendingActions[item.group] || 0 }}
        </span>
      </button>
    </div>
  </div>
</template>
