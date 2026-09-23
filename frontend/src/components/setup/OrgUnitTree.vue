<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Dropdown, FeatherIcon } from 'frappe-ui'
import EmptyState from '@/components/common/EmptyState.vue'
import type { OrgTreeIndex } from '@/utils/orgTree'
import type { OrgUnit } from '@/types/setup'

const props = defineProps<{
  index: OrgTreeIndex
  /** ao_unit -> IRB Unit name, for the "IRB" badge. */
  irbUnitByAo: Map<string, string>
  /** ao_unit -> number of faculty memberships. */
  facultyCountByAo: Map<string, number>
  search: string
}>()

const emit = defineEmits<{
  'add-child': [OrgUnit]
  edit: [OrgUnit]
  delete: [OrgUnit]
  'setup-irb': [OrgUnit]
}>()

const collapsed = ref(new Set<string>())

const narrowQuery = typeof window !== 'undefined' ? window.matchMedia('(max-width: 639px)') : null
const isNarrow = ref(narrowQuery?.matches ?? false)
const onNarrowChange = (e: MediaQueryListEvent) => (isNarrow.value = e.matches)
onMounted(() => narrowQuery?.addEventListener('change', onNarrowChange))
onBeforeUnmount(() => narrowQuery?.removeEventListener('change', onNarrowChange))

function toggle(name: string) {
  const next = new Set(collapsed.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  collapsed.value = next
}

function setAll(collapse: boolean) {
  collapsed.value = collapse
    ? new Set(props.index.ordered.filter((u) => props.index.children.get(u.name)?.length).map((u) => u.name))
    : new Set()
}
defineExpose({ expandAll: () => setAll(false), collapseAll: () => setAll(true) })

// While searching, show every match plus its ancestors (so it stays in
// context) and ignore collapse state; otherwise honour collapsed nodes.
const visible = computed(() => {
  const term = props.search.trim().toLowerCase()
  if (term) {
    const keep = new Set<string>()
    for (const u of props.index.ordered) {
      if (![u.ao_name, u.ao_code, u.name, u.ao_type].some((v) => v?.toLowerCase().includes(term))) continue
      let cur: OrgUnit | undefined = u
      while (cur && !keep.has(cur.name)) {
        keep.add(cur.name)
        cur = cur.parent ? props.index.byName.get(cur.parent) : undefined
      }
    }
    return props.index.ordered.filter((u) => keep.has(u.name))
  }
  // `ordered` is depth-first, so a collapsed node's descendants are exactly
  // the run of following nodes that sit deeper than it.
  const out: OrgUnit[] = []
  let skipDeeperThan = Infinity
  for (const u of props.index.ordered) {
    const depth = props.index.depth(u.name)
    if (depth > skipDeeperThan) continue
    skipDeeperThan = collapsed.value.has(u.name) ? depth : Infinity
    out.push(u)
  }
  return out
})

// Edit / Add Child / Delete sit inline on the row (as in the Desk tree
// view); the less common shortcuts live in the overflow menu.
function menuFor(u: OrgUnit) {
  const items = []
  // Below `sm` the inline buttons are hidden, so fold them into the menu.
  if (isNarrow.value) {
    items.push({ label: 'Edit', icon: 'edit-2', onClick: () => emit('edit', u) })
    if (u.is_group) items.push({ label: 'Add Child', icon: 'plus', onClick: () => emit('add-child', u) })
  }
  if (!props.irbUnitByAo.has(u.name)) items.push({ label: 'Set up IRB Unit', icon: 'shield', onClick: () => emit('setup-irb', u) })
  if (isNarrow.value) items.push({ label: 'Delete', icon: 'trash-2', theme: 'red' as const, onClick: () => emit('delete', u) })
  return items
}

const TYPE_TONE: Record<string, string> = {
  University: 'bg-primary/10 text-primary',
  Campus: 'bg-blue-50 text-info',
  School: 'bg-emerald-50 text-success',
  Department: 'bg-amber-50 text-warning',
  Programme: 'bg-canvas text-muted',
}
</script>

<template>
  <div>
    <EmptyState
      v-if="!visible.length"
      icon="git-branch"
      :title="search ? 'No units match your search' : 'No units yet'"
      :description="search ? undefined : 'Start with your top-level unit (e.g. the university), then add campuses, schools and programmes under it.'"
    />
    <ul v-else class="divide-y divide-line overflow-hidden rounded-lg border border-line">
      <li
        v-for="u in visible"
        :key="u.name"
        class="group flex items-center gap-2 bg-paper py-2 pr-2 transition-colors hover:bg-canvas"
        :style="{ paddingLeft: `${12 + index.depth(u.name) * 22}px` }"
      >
        <button
          v-if="index.children.get(u.name)?.length && !search"
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-muted hover:bg-paper hover:text-charcoal"
          :aria-label="collapsed.has(u.name) ? `Expand ${u.ao_name}` : `Collapse ${u.ao_name}`"
          @click="toggle(u.name)"
        >
          <FeatherIcon :name="collapsed.has(u.name) ? 'chevron-right' : 'chevron-down'" class="h-4 w-4" />
        </button>
        <span v-else class="h-6 w-6 shrink-0" />

        <FeatherIcon :name="u.is_group ? 'folder' : 'file'" class="h-4 w-4 shrink-0 text-muted" />

        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <button class="truncate text-left text-sm font-medium text-charcoal hover:text-primary" @click="emit('edit', u)">
              {{ u.ao_name }}
            </button>
            <span class="rounded-full px-2 py-0.5 text-[11px] font-medium" :class="TYPE_TONE[u.ao_type] || TYPE_TONE.Programme">
              {{ u.ao_type }}
            </span>
            <span
              v-if="irbUnitByAo.has(u.name)"
              class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-success"
              title="This unit has an IRB Unit"
            >
              <FeatherIcon name="shield" class="h-3 w-3" /> IRB
            </span>
          </div>
          <p class="truncate text-xs text-muted">
            <span class="font-mono">{{ u.name }}</span>
            <template v-if="facultyCountByAo.get(u.name)"> · {{ facultyCountByAo.get(u.name) }} faculty</template>
          </p>
        </div>

        <!-- Always visible on touch screens; revealed on hover/focus on desktop. -->
        <div
          class="flex shrink-0 items-center gap-1 transition-opacity md:opacity-0 md:focus-within:opacity-100 md:group-hover:opacity-100"
        >
          <div class="hidden divide-x divide-line overflow-hidden rounded-md border border-line bg-paper text-sm sm:flex">
            <button class="px-2.5 py-1 font-medium text-charcoal hover:bg-canvas" @click="emit('edit', u)">Edit</button>
            <button v-if="u.is_group" class="px-2.5 py-1 font-medium text-charcoal hover:bg-canvas" @click="emit('add-child', u)">
              Add Child
            </button>
            <button class="px-2.5 py-1 font-medium text-danger hover:bg-danger/5" @click="emit('delete', u)">Delete</button>
          </div>
          <Dropdown
            v-if="menuFor(u).length"
            :options="menuFor(u)"
            placement="right"
          >
            <button
              class="flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-paper hover:text-charcoal"
              :aria-label="`More actions for ${u.ao_name}`"
            >
              <FeatherIcon name="more-horizontal" class="h-4 w-4" />
            </button>
          </Dropdown>
          <span v-else class="h-8 w-8" />
        </div>
      </li>
    </ul>
  </div>
</template>
