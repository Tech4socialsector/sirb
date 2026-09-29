<script setup lang="ts">
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ApprovalTimeline from '@/components/projects/ApprovalTimeline.vue'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import { PROJECT_STATUSES } from '@/types/project'

const { state, close } = useTimelineDrawer()

// Canonical forward stages the project hasn't reached yet, so reviewers/
// students can see what's still ahead — not just what already happened.
// Branch/correction statuses (e.g. "Awaiting student correction...") only
// ever appear in `history` itself, never here, since they aren't a fixed
// forward stage every project passes through.
const upcomingStatuses = computed(() => {
  if (!state.currentStatus) return []
  const currentIndex = PROJECT_STATUSES.indexOf(state.currentStatus as (typeof PROJECT_STATUSES)[number])
  if (currentIndex === -1) return []
  return PROJECT_STATUSES.slice(currentIndex + 1).filter((s) => !s.startsWith('Awaiting student correction'))
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-150"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div v-if="state.isOpen" class="fixed inset-0 z-[100] flex justify-end">
        <div class="absolute inset-0 bg-charcoal/40" @click="close" />
        <Transition
          appear
          enter-active-class="transition-transform duration-200 ease-out"
          leave-active-class="transition-transform duration-150 ease-in"
          enter-from-class="translate-x-full"
          leave-to-class="translate-x-full"
        >
          <aside
            v-if="state.isOpen"
            class="relative flex h-full w-full max-w-md flex-col bg-paper shadow-xl sm:max-w-lg"
          >
            <header class="flex shrink-0 items-start justify-between gap-3 border-b border-line px-5 py-4">
              <div class="min-w-0">
                <h2 class="text-base font-semibold text-charcoal">Project Timeline</h2>
                <p v-if="state.projectTitle" class="mt-1 truncate text-sm text-muted">{{ state.projectTitle }}</p>
                <p v-if="state.studentName" class="mt-0.5 text-sm text-muted">Student: {{ state.studentName }}</p>
              </div>
              <button
                class="shrink-0 rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-charcoal"
                aria-label="Close timeline"
                @click="close"
              >
                <FeatherIcon name="x" class="h-5 w-5" />
              </button>
            </header>

            <div v-if="state.currentStatus" class="shrink-0 border-b border-line bg-canvas px-5 py-3">
              <p class="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted">Current Status</p>
              <StatusBadge :status="state.currentStatus" />
            </div>

            <div class="flex-1 overflow-y-auto sirb-scrollbar px-5 py-4">
              <EmptyState
                v-if="!state.loading && !state.history.length"
                icon="clock"
                title="No status changes yet"
                description="This project hasn't moved through any approval stages yet."
              />
              <ApprovalTimeline v-else :history="[...state.history]" :loading="state.loading" bare stacked />

              <div v-if="upcomingStatuses.length" class="mt-2">
                <p class="mb-3 text-xs font-medium uppercase tracking-wide text-muted">Upcoming</p>
                <ol class="space-y-3">
                  <li v-for="status in upcomingStatuses" :key="status" class="flex items-center gap-3">
                    <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-canvas text-muted">
                      <FeatherIcon name="circle" class="h-3 w-3" />
                    </span>
                    <span class="text-sm text-muted">{{ status }}</span>
                  </li>
                </ol>
              </div>
            </div>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
