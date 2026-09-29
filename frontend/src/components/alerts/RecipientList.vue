<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { RecipientPreview, RecipientRow } from '@/types/alerts'
import { daysBetween, formatServerDate, relativeDays } from '@/utils/serverTime'

/** The preview's student-project rows, grouped into one card per student. */
const props = defineProps<{ preview: RecipientPreview; serverNow: string }>()

const PAGE = 15
const view = ref<'sendable' | 'skipped'>('sendable')
const search = ref('')
const shown = ref(PAGE)
watch([view, search, () => props.preview], () => (shown.value = PAGE))

interface StudentGroup {
  student: string
  student_name: string
  student_id: string | null
  email: string
  programmes: string[]
  reasons: string[]
  projects: RecipientRow[]
}

function group(rows: RecipientRow[]): StudentGroup[] {
  const map = new Map<string, StudentGroup>()
  for (const r of rows) {
    let g = map.get(r.student)
    if (!g) {
      g = { student: r.student, student_name: r.student_name, student_id: r.student_id, email: r.email, programmes: [], reasons: [], projects: [] }
      map.set(r.student, g)
    }
    if (r.programme && !g.programmes.includes(r.programme)) g.programmes.push(r.programme)
    if (r.reason && !g.reasons.includes(r.reason)) g.reasons.push(r.reason)
    g.projects.push(r)
  }
  return [...map.values()]
}

const groups = computed(() => group(view.value === 'sendable' ? props.preview.sendable : props.preview.skipped))
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return groups.value
  return groups.value.filter((g) =>
    [g.student_name, g.student_id, g.email, ...g.programmes, ...g.projects.flatMap((p) => [String(p.irb_project), p.project_title, p.project_status])]
      .some((v) => v && String(v).toLowerCase().includes(q)),
  )
})
const visible = computed(() => filtered.value.slice(0, shown.value))
const truncated = computed(() => {
  const total = view.value === 'sendable' ? props.preview.sendable_count : props.preview.skipped_count
  return total > props.preview.row_limit
})

function initials(name: string) {
  return (name || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join('')
}
function projectLabel(p: RecipientRow) {
  const title = (p.project_title || '').trim()
  return title ? title : 'No title yet'
}
function updated(p: RecipientRow) {
  const days = daysBetween(p.project_modified, props.serverNow)
  return { rel: relativeDays(days), date: formatServerDate(p.project_modified), stale: days !== null && days >= 14 }
}
</script>

<template>
  <div class="rounded-lg border border-line bg-paper">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
      <div class="inline-flex rounded-lg border border-line bg-canvas p-0.5 text-xs font-medium" role="tablist">
        <button
          type="button"
          role="tab"
          :aria-selected="view === 'sendable'"
          class="rounded-md px-3 py-1"
          :class="view === 'sendable' ? 'bg-paper text-charcoal shadow-sm' : 'text-muted hover:text-charcoal'"
          @click="view = 'sendable'"
        >
          Will receive · {{ preview.unique_students }} student{{ preview.unique_students === 1 ? '' : 's' }}
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="view === 'skipped'"
          class="rounded-md px-3 py-1"
          :class="view === 'skipped' ? 'bg-paper text-charcoal shadow-sm' : 'text-muted hover:text-charcoal'"
          @click="view = 'skipped'"
        >
          Skipped · {{ preview.skipped_count }}
        </button>
      </div>
      <div class="relative w-full sm:w-64">
        <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-muted" />
        <input
          v-model="search"
          type="text"
          placeholder="Search name, e-mail, project…"
          class="h-7 w-full rounded border border-line bg-canvas pl-8 pr-2 text-xs text-charcoal placeholder:text-muted focus:border-primary focus:outline-none focus:ring-0"
        />
      </div>
    </div>

    <div v-if="!filtered.length" class="px-4 py-10 text-center text-sm text-muted">
      <template v-if="search">No one matches “{{ search }}”.</template>
      <template v-else-if="view === 'sendable'">Nobody will receive this e-mail with the current selection.</template>
      <template v-else>Nobody is skipped — every matching student has an e-mail address.</template>
    </div>

    <ul v-else class="divide-y divide-line">
      <li v-for="g in visible" :key="g.student" class="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-start">
        <div class="flex min-w-0 items-start gap-3 md:w-72 md:shrink-0">
          <span
            class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
            :class="view === 'skipped' ? 'bg-amber-50 text-warning' : 'bg-canvas text-charcoal'"
            aria-hidden="true"
            >{{ initials(g.student_name) }}</span
          >
          <div class="min-w-0">
            <p class="truncate text-sm font-medium text-charcoal">{{ g.student_name }}</p>
            <p v-if="view === 'sendable'" class="truncate text-xs text-muted">{{ g.email }}</p>
            <p v-else class="mt-0.5 flex flex-wrap gap-1">
              <span v-for="r in g.reasons" :key="r" class="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-warning">{{ r }}</span>
            </p>
            <p v-if="g.programmes.length" class="truncate text-xs text-muted">{{ g.programmes.join(', ') }}</p>
          </div>
        </div>

        <div class="min-w-0 flex-1">
          <p class="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted">
            {{ g.projects.length }} project{{ g.projects.length === 1 ? '' : 's' }}
            <template v-if="view === 'sendable'"> · {{ g.projects.length }} e-mail{{ g.projects.length === 1 ? '' : 's' }}</template>
          </p>
          <ul class="space-y-1.5">
            <li
              v-for="p in g.projects"
              :key="p.irb_project"
              class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-line px-3 py-1.5"
            >
              <RouterLink :to="`/sirb/projects/${p.irb_project}`" target="_blank" class="shrink-0 text-xs font-semibold text-primary hover:underline">
                #{{ p.irb_project }}
              </RouterLink>
              <span class="min-w-0 flex-1 truncate text-sm" :class="p.project_title ? 'text-charcoal' : 'italic text-muted'">{{ projectLabel(p) }}</span>
              <StatusBadge :status="p.project_status" />
              <span class="shrink-0 text-xs" :class="updated(p).stale ? 'text-warning' : 'text-muted'" :title="`Last updated ${updated(p).date}`">
                <FeatherIcon name="clock" class="-mt-0.5 mr-0.5 inline h-3 w-3" />{{ updated(p).rel }}
              </span>
            </li>
          </ul>
        </div>
      </li>
    </ul>

    <div v-if="filtered.length" class="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2.5 text-xs text-muted">
      <span>
        Showing {{ visible.length }} of {{ filtered.length }} student{{ filtered.length === 1 ? '' : 's' }}
        <template v-if="truncated"> (preview lists the first {{ preview.row_limit }} projects; sending includes everyone)</template>
      </span>
      <button v-if="visible.length < filtered.length" type="button" class="font-medium text-primary hover:underline" @click="shown += PAGE">
        Show {{ Math.min(PAGE, filtered.length - visible.length) }} more
      </button>
    </div>
  </div>
</template>
