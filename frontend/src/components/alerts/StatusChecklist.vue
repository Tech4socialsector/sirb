<script setup lang="ts">
import { computed } from 'vue'
import { groupsFor } from '@/utils/statusGroups'

/**
 * Which project statuses get the e-mail. `modelValue` is `null` for "every
 * status" (no status filter) and a list otherwise — an empty list means
 * nobody, never everybody, so the page blocks sending on it.
 */
const props = defineProps<{
  statuses: string[]
  modelValue: string[] | null
  /** E-mails per status for the current recipients (before this filter). */
  counts: Record<string, number> | null
  loading?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [string[] | null] }>()

const groups = computed(() => groupsFor(props.statuses))

const selected = computed(() => new Set(props.modelValue ?? props.statuses))
const isChecked = (s: string) => selected.value.has(s)
const count = (s: string) => props.counts?.[s] ?? 0

function commit(next: Set<string>) {
  // Keep workflow order; "all" is stored as null (no filter).
  const list = props.statuses.filter((s) => next.has(s))
  emit('update:modelValue', list.length === props.statuses.length ? null : list)
}
function toggle(s: string) {
  const next = new Set(selected.value)
  if (next.has(s)) next.delete(s)
  else next.add(s)
  commit(next)
}
function groupState(g: { statuses: string[] }) {
  const on = g.statuses.filter(isChecked).length
  return on === 0 ? 'none' : on === g.statuses.length ? 'all' : 'some'
}
function toggleGroup(g: { statuses: string[] }) {
  const next = new Set(selected.value)
  const turnOn = groupState(g) !== 'all'
  for (const s of g.statuses) {
    if (turnOn) next.add(s)
    else next.delete(s)
  }
  commit(next)
}
const groupCount = (g: { statuses: string[] }) => g.statuses.reduce((n, s) => n + count(s), 0)
const selectedEmails = computed(() => props.statuses.filter(isChecked).reduce((n, s) => n + count(s), 0))

const summary = computed(() => {
  if (props.modelValue === null) return 'All statuses'
  if (!props.modelValue.length) return 'No status selected'
  return `${props.modelValue.length} of ${props.statuses.length} statuses`
})
</script>

<template>
  <div class="rounded-lg border border-line">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-canvas px-4 py-2.5">
      <div>
        <p class="text-sm font-medium text-charcoal">Send for these project statuses</p>
        <p class="text-xs text-muted">
          {{ summary }}<template v-if="counts"> · {{ selectedEmails }} e-mail{{ selectedEmails === 1 ? '' : 's' }}</template>
          <span v-if="loading" class="ml-1 animate-pulse">· updating…</span>
        </p>
      </div>
      <div class="flex items-center gap-3 text-xs font-medium">
        <button type="button" class="text-primary hover:underline disabled:opacity-40 disabled:no-underline" :disabled="modelValue === null" @click="emit('update:modelValue', null)">
          Select all
        </button>
        <button type="button" class="text-primary hover:underline disabled:opacity-40 disabled:no-underline" :disabled="modelValue !== null && !modelValue.length" @click="emit('update:modelValue', [])">
          Clear
        </button>
      </div>
    </div>

    <div class="grid gap-px bg-line sm:grid-cols-2 xl:grid-cols-4">
      <fieldset v-for="g in groups" :key="g.label" class="min-w-0 bg-paper p-3">
        <legend class="sr-only">{{ g.label }}</legend>
        <label class="mb-2 flex cursor-pointer items-start gap-2">
          <input
            type="checkbox"
            class="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            :checked="groupState(g) === 'all'"
            :indeterminate="groupState(g) === 'some'"
            :aria-label="`All ${g.label}`"
            @change="toggleGroup(g)"
          />
          <span class="min-w-0 flex-1">
            <span class="flex items-center justify-between gap-2">
              <span class="text-xs font-semibold uppercase tracking-wide text-charcoal">{{ g.label }}</span>
              <span v-if="counts" class="text-xs text-muted">{{ groupCount(g) }}</span>
            </span>
            <span v-if="g.hint" class="block text-[11px] text-muted">{{ g.hint }}</span>
          </span>
        </label>
        <ul class="space-y-1 pl-6">
          <li v-for="s in g.statuses" :key="s">
            <label class="flex cursor-pointer items-start gap-2 rounded px-1 py-0.5 hover:bg-canvas" :class="counts && !count(s) ? 'opacity-60' : ''">
              <input
                type="checkbox"
                class="mt-0.5 h-3.5 w-3.5 shrink-0 rounded border-gray-300 text-primary focus:ring-primary"
                :checked="isChecked(s)"
                @change="toggle(s)"
              />
              <span class="min-w-0 flex-1 text-sm leading-snug text-charcoal">{{ s }}</span>
              <span
                v-if="counts"
                class="shrink-0 rounded-full px-1.5 text-xs font-medium"
                :class="count(s) ? 'bg-canvas text-charcoal' : 'text-muted'"
                :title="`${count(s)} e-mail${count(s) === 1 ? '' : 's'}`"
                >{{ count(s) }}</span
              >
            </label>
          </li>
        </ul>
      </fieldset>
    </div>
  </div>
</template>
