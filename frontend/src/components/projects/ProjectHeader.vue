<script setup lang="ts">
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { IrbProjectDoc, ProjectRoles } from '@/types/project'

const props = defineProps<{ doc: IrbProjectDoc; roles: ProjectRoles }>()

function introRole() {
  if (props.roles.is_mentor) return 'faculty mentor'
  if (props.roles.is_primary_reviewer) return 'primary IRB reviewer'
  if (props.roles.is_secondary_reviewer) return 'secondary IRB reviewer'
  return null
}
</script>

<template>
  <div class="mb-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-charcoal">{{ doc.title || 'Untitled Project' }}</h1>
        <p class="mt-0.5 text-sm text-muted">{{ doc.name }} · Cycle {{ doc.irb_cycle || '—' }}</p>
      </div>
      <StatusBadge :status="doc.status" />
    </div>
    <div
      v-if="introRole()"
      class="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
    >
      You are the {{ introRole() }} for this IRB project.
    </div>
  </div>
</template>
