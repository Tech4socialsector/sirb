<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import Breadcrumbs from './Breadcrumbs.vue'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import { useRoles } from '@/composables/useRoles'

const emit = defineEmits<{ 'toggle-mobile-nav': [] }>()

const router = useRouter()
const { state, open: openTimeline } = useTimelineDrawer()
const { isAdmin } = useRoles()

// Jumps straight to a project by its ID — there's no project search API on
// the backend today, so this stays scoped to what's actually possible
// rather than faking a fuzzy-search experience.
const searchValue = ref('')
function goToProject() {
  const value = searchValue.value.trim()
  if (!value) return
  router.push(`/sirb/projects/${encodeURIComponent(value)}`)
  searchValue.value = ''
}
</script>

<template>
  <header class="flex h-16 shrink-0 items-center gap-3 border-b border-line bg-paper px-4 md:px-6">
    <button class="p-1 text-muted md:hidden" @click="emit('toggle-mobile-nav')">
      <FeatherIcon name="menu" class="h-5 w-5" />
    </button>

    <div class="min-w-0 flex-1">
      <Breadcrumbs />
    </div>

    <div class="flex shrink-0 items-center gap-2">
      <div class="relative hidden sm:block">
        <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          v-model="searchValue"
          type="text"
          placeholder="Go to project ID…"
          class="w-44 rounded-md border border-line bg-canvas py-1.5 pl-8 pr-2 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary lg:w-56"
          @keyup.enter="goToProject"
        />
      </div>

      <a
        v-if="isAdmin"
        href="/app"
        target="_blank"
        rel="noopener"
        class="hidden items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-charcoal transition-colors hover:bg-canvas sm:flex"
      >
        <FeatherIcon name="grid" class="h-4 w-4" />
        Go to Desk
      </a>

      <button
        v-if="state.projectName"
        class="flex items-center gap-1.5 rounded-md border border-line px-3 py-1.5 text-sm font-medium text-charcoal transition-colors hover:bg-canvas"
        @click="openTimeline"
      >
        <FeatherIcon name="clock" class="h-4 w-4" />
        <span class="hidden sm:inline">Timeline</span>
      </button>
    </div>
  </header>
</template>
