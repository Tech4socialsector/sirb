<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import { searchStudents } from '@/services/alerts'
import type { StudentOption } from '@/types/alerts'

/**
 * Pick students from a list that is shown right away (first 50,
 * alphabetically, within the timeline's unit/cycle) and narrows as you
 * type. Each row is a checkbox, so picking and un-picking work the same way.
 */
const MAX_PICKED = 500 // same limit as the server (MAX_PICKED_STUDENTS)

const props = defineProps<{ modelValue: StudentOption[]; timeline?: string | null }>()
const emit = defineEmits<{ 'update:modelValue': [StudentOption[]] }>()

const query = ref('')
const results = ref<StudentOption[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const active = ref(-1)
let seq = 0
let timer: ReturnType<typeof setTimeout> | undefined

const pickedNames = computed(() => new Set(props.modelValue.map((s) => s.student)))
const isPicked = (s: StudentOption) => pickedNames.value.has(s.student)
const full = computed(() => props.modelValue.length >= MAX_PICKED)

async function run() {
  const mine = ++seq
  loading.value = true
  error.value = ''
  try {
    const r = await searchStudents(query.value.trim(), props.timeline ?? null)
    if (mine !== seq) return // a newer search is on its way
    results.value = r.rows
    total.value = r.total
    active.value = -1
  } catch (e) {
    if (mine !== seq) return
    results.value = []
    total.value = 0
    error.value = e instanceof Error ? e.message : 'Could not load students.'
  } finally {
    if (mine === seq) loading.value = false
  }
}
watch(query, () => {
  clearTimeout(timer)
  loading.value = true
  timer = setTimeout(run, 250)
})
watch(() => props.timeline, run)
onMounted(run)
onUnmounted(() => clearTimeout(timer))

function toggle(s: StudentOption) {
  if (isPicked(s)) emit('update:modelValue', props.modelValue.filter((x) => x.student !== s.student))
  else if (!full.value) emit('update:modelValue', [...props.modelValue, s])
}
function remove(name: string) {
  emit('update:modelValue', props.modelValue.filter((s) => s.student !== name))
}
const allShownPicked = computed(() => results.value.length > 0 && results.value.every(isPicked))
function toggleAllShown() {
  if (allShownPicked.value) {
    const shown = new Set(results.value.map((r) => r.student))
    emit('update:modelValue', props.modelValue.filter((s) => !shown.has(s.student)))
  } else {
    const add = results.value.filter((r) => !isPicked(r)).slice(0, MAX_PICKED - props.modelValue.length)
    emit('update:modelValue', [...props.modelValue, ...add])
  }
}

function onKeydown(e: KeyboardEvent) {
  const n = results.value.length
  if (!n) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    active.value = (active.value + 1) % n
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    active.value = (active.value - 1 + n) % n
  } else if (e.key === 'Enter') {
    e.preventDefault()
    toggle(results.value[Math.max(active.value, 0)])
  }
}
watch(active, (i) => {
  if (i >= 0) document.getElementById(`sp-row-${i}`)?.scrollIntoView({ block: 'nearest' })
})

const noEmail = (s: StudentOption) => !s.email || !s.user_enabled
const meta = (s: StudentOption) =>
  [s.student_id && s.student_id !== s.student_name ? s.student_id : null, s.programme, `${s.project_count} project${s.project_count === 1 ? '' : 's'}`]
    .filter(Boolean)
    .join(' · ')
</script>

<template>
  <div class="rounded-lg border border-line">
    <!-- picked -->
    <div class="border-b border-line bg-canvas px-3 py-2.5">
      <div class="flex items-center justify-between gap-2">
        <p class="text-xs font-medium text-charcoal">
          {{ modelValue.length ? `${modelValue.length} student${modelValue.length === 1 ? '' : 's'} selected` : 'No students selected yet' }}
        </p>
        <button v-if="modelValue.length" type="button" class="text-xs font-medium text-primary hover:underline" @click="emit('update:modelValue', [])">Clear selection</button>
      </div>
      <ul v-if="modelValue.length" class="mt-2 flex max-h-24 flex-wrap gap-1.5 overflow-y-auto sirb-scrollbar">
        <li
          v-for="s in modelValue"
          :key="s.student"
          class="flex max-w-full items-center gap-1.5 rounded-full border py-0.5 pl-2.5 pr-1 text-xs"
          :class="noEmail(s) ? 'border-amber-200 bg-amber-50' : 'border-line bg-paper'"
          :title="noEmail(s) ? 'No active user account with an e-mail address — this student will be skipped.' : s.email || ''"
        >
          <span class="truncate text-charcoal">{{ s.student_name }}</span>
          <FeatherIcon v-if="noEmail(s)" name="alert-triangle" class="h-3 w-3 shrink-0 text-warning" />
          <button type="button" class="rounded-full p-0.5 text-muted hover:text-danger" :aria-label="`Remove ${s.student_name}`" @click="remove(s.student)">
            <FeatherIcon name="x" class="h-3 w-3" />
          </button>
        </li>
      </ul>
    </div>

    <!-- search -->
    <div class="relative border-b border-line">
      <FeatherIcon name="search" class="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
      <input
        v-model="query"
        type="text"
        aria-label="Search students"
        placeholder="Filter by name, student ID or e-mail…"
        class="h-9 w-full border-0 bg-paper pl-9 pr-3 text-sm text-charcoal placeholder:text-muted focus:outline-none focus:ring-0"
        @keydown="onKeydown"
      />
      <FeatherIcon v-if="loading" name="loader" class="absolute right-3 top-2.5 h-4 w-4 animate-spin text-muted" />
    </div>

    <!-- list -->
    <div class="flex items-center justify-between gap-2 border-b border-line px-3 py-1.5 text-xs text-muted">
      <span>
        <template v-if="error"><span class="text-danger">{{ error }}</span></template>
        <template v-else-if="total > results.length">Showing {{ results.length }} of {{ total }} — type to narrow the list</template>
        <template v-else>{{ total }} student{{ total === 1 ? '' : 's' }}{{ query.trim() ? ` matching “${query.trim()}”` : '' }}</template>
      </span>
      <button v-if="results.length" type="button" class="font-medium text-primary hover:underline disabled:opacity-40" :disabled="full && !allShownPicked" @click="toggleAllShown">
        {{ allShownPicked ? 'Unselect shown' : `Select all ${results.length} shown` }}
      </button>
    </div>
    <ul class="max-h-64 overflow-y-auto sirb-scrollbar" role="listbox" aria-multiselectable="true" aria-label="Students">
      <li v-if="!loading && !error && !results.length" class="px-3 py-6 text-center text-sm text-muted">
        {{ query.trim() ? `No student matches “${query.trim()}”.` : 'No students have a project yet.' }}
      </li>
      <li
        v-for="(s, i) in results"
        :id="`sp-row-${i}`"
        :key="s.student"
        role="option"
        :aria-selected="isPicked(s)"
        class="flex cursor-pointer items-center gap-3 border-b border-line px-3 py-2 last:border-b-0"
        :class="[i === active ? 'bg-canvas' : 'hover:bg-canvas', !isPicked(s) && full ? 'cursor-not-allowed opacity-50' : '']"
        @click="toggle(s)"
        @mouseenter="active = i"
      >
        <input
          type="checkbox"
          tabindex="-1"
          class="pointer-events-none h-4 w-4 shrink-0 rounded border-gray-300 text-primary focus:ring-primary"
          :checked="isPicked(s)"
          :aria-label="s.student_name"
        />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-medium text-charcoal">{{ s.student_name }}</span>
          <span class="block truncate text-xs text-muted">{{ meta(s) }}</span>
        </span>
        <span class="hidden shrink-0 text-xs sm:block" :class="noEmail(s) ? 'text-warning' : 'text-muted'">{{ noEmail(s) ? 'No e-mail' : s.email }}</span>
      </li>
    </ul>
    <p v-if="full" class="border-t border-line px-3 py-1.5 text-xs text-warning">Limit of {{ MAX_PICKED }} students reached — use “By project status” for bigger groups.</p>
  </div>
</template>
