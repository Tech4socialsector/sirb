<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import { searchStudents } from '@/services/alerts'
import type { StudentOption } from '@/types/alerts'

const MAX_PICKED = 500 // same limit as the server (MAX_PICKED_STUDENTS)

const props = defineProps<{ modelValue: StudentOption[] }>()
const emit = defineEmits<{ 'update:modelValue': [StudentOption[]] }>()

const query = ref('')
const results = ref<StudentOption[]>([])
const loading = ref(false)
const error = ref('')
const open = ref(false)
const active = ref(0)
let seq = 0
let timer: ReturnType<typeof setTimeout> | undefined

const pickedNames = computed(() => new Set(props.modelValue.map((s) => s.student)))
const visibleResults = computed(() => results.value.filter((r) => !pickedNames.value.has(r.student)))
const full = computed(() => props.modelValue.length >= MAX_PICKED)

watch(query, (q) => {
  clearTimeout(timer)
  error.value = ''
  active.value = 0
  if (q.trim().length < 2) {
    seq++ // drop any response still in flight for the old query
    results.value = []
    loading.value = false
    return
  }
  loading.value = true
  timer = setTimeout(() => run(q.trim()), 250)
})

async function run(q: string) {
  const mine = ++seq
  try {
    const rows = await searchStudents(q)
    if (mine === seq) results.value = rows
  } catch (e) {
    if (mine === seq) {
      results.value = []
      error.value = e instanceof Error ? e.message : 'Search failed.'
    }
  } finally {
    if (mine === seq) loading.value = false
  }
}

function add(s: StudentOption) {
  if (full.value || pickedNames.value.has(s.student)) return
  emit('update:modelValue', [...props.modelValue, s])
  // Keep the query so several students from one search can be added.
  active.value = Math.min(active.value, Math.max(visibleResults.value.length - 2, 0))
}
function remove(name: string) {
  emit('update:modelValue', props.modelValue.filter((s) => s.student !== name))
}

function onKeydown(e: KeyboardEvent) {
  const list = visibleResults.value
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    open.value = true
    active.value = list.length ? (active.value + 1) % list.length : 0
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    active.value = list.length ? (active.value - 1 + list.length) % list.length : 0
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (list[active.value]) add(list[active.value])
  } else if (e.key === 'Escape') {
    open.value = false
  }
}

function noEmail(s: StudentOption) {
  return !s.email || !s.user_enabled
}

onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <div>
    <!-- Chips sit above the search box so its results list never covers them. -->
    <div v-if="modelValue.length" class="mb-3">
      <div class="mb-2 flex items-center justify-between text-xs text-muted">
        <span>{{ modelValue.length }} student{{ modelValue.length === 1 ? '' : 's' }} selected</span>
        <button type="button" class="font-medium text-primary hover:underline" @click="emit('update:modelValue', [])">Clear all</button>
      </div>
      <ul class="flex flex-wrap gap-2">
        <li
          v-for="s in modelValue"
          :key="s.student"
          class="flex max-w-full items-center gap-2 rounded-full border py-1 pl-3 pr-1.5 text-sm"
          :class="noEmail(s) ? 'border-amber-200 bg-amber-50' : 'border-line bg-canvas'"
          :title="noEmail(s) ? 'No active user account with an e-mail address — this student will be skipped.' : s.email || ''"
        >
          <span class="truncate text-charcoal">{{ s.student_name }}</span>
          <FeatherIcon v-if="noEmail(s)" name="alert-triangle" class="h-3.5 w-3.5 shrink-0 text-warning" />
          <button
            type="button"
            class="rounded-full p-0.5 text-muted hover:bg-paper hover:text-danger"
            :aria-label="`Remove ${s.student_name}`"
            @click="remove(s.student)"
          >
            <FeatherIcon name="x" class="h-3.5 w-3.5" />
          </button>
        </li>
      </ul>
    </div>
    <p v-else class="mb-2 text-xs text-muted">Pick one student, or several for a group. Each gets one e-mail per project they're on.</p>
    <div class="relative">
      <FeatherIcon name="search" class="pointer-events-none absolute left-2.5 top-2 h-4 w-4 text-muted" />
      <input
        v-model="query"
        type="text"
        role="combobox"
        aria-label="Search students"
        :aria-expanded="open && query.trim().length >= 2"
        :disabled="full"
        :placeholder="full ? `Limit of ${MAX_PICKED} students reached` : 'Search students by name, ID or e-mail…'"
        class="h-8 w-full rounded border border-line bg-canvas pl-8 pr-3 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none focus:ring-0 disabled:opacity-60"
        @focus="open = true"
        @blur="open = false"
        @keydown="onKeydown"
      />
      <div
        v-if="open && query.trim().length >= 2"
        class="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-line bg-paper shadow-lg sirb-scrollbar"
        role="listbox"
        @mousedown.prevent
      >
        <p v-if="loading && !visibleResults.length" class="px-3 py-2.5 text-sm text-muted">Searching…</p>
        <p v-else-if="error" class="px-3 py-2.5 text-sm text-danger">{{ error }}</p>
        <p v-else-if="!visibleResults.length" class="px-3 py-2.5 text-sm text-muted">
          {{ results.length ? 'All matching students are already added.' : 'No students with a project match.' }}
        </p>
        <button
          v-for="(s, i) in visibleResults"
          :key="s.student"
          type="button"
          role="option"
          :aria-selected="i === active"
          class="flex w-full items-start justify-between gap-3 px-3 py-2 text-left"
          :class="i === active ? 'bg-canvas' : 'hover:bg-canvas'"
          @mouseenter="active = i"
          @click="add(s)"
        >
          <span class="min-w-0">
            <span class="block truncate text-sm font-medium text-charcoal">{{ s.student_name }}</span>
            <span class="block truncate text-xs text-muted">
              {{ [s.student_id !== s.student_name ? s.student_id : null, s.programme, `${s.project_count} project${s.project_count === 1 ? '' : 's'}`].filter(Boolean).join(' · ') }}
            </span>
          </span>
          <span class="shrink-0 text-xs" :class="noEmail(s) ? 'text-warning' : 'text-muted'">
            {{ noEmail(s) ? 'No e-mail' : s.email }}
          </span>
        </button>
      </div>
    </div>

  </div>
</template>
