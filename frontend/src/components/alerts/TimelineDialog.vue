<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { Button, Dialog, FeatherIcon, FormControl, Switch } from 'frappe-ui'
import { parseActivities, saveTimeline } from '@/services/alerts'
import type { IrbTimeline, ParsedActivity, UnitOption } from '@/types/alerts'
import { daysBetween, relativeDays } from '@/utils/serverTime'
import { groupsFor, type StatusGroup } from '@/utils/statusGroups'

const props = defineProps<{
  modelValue: boolean
  timeline: IrbTimeline | null
  units: UnitOption[]
  cycles: string[]
  statuses: string[]
  serverNow: string
}>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [string] }>()

// ---------------------------------------------------------------- model
interface Row {
  key: number
  name?: string
  activity: string
  start_date: string
  /** Only used while `ranged`. */
  end_date: string
  ranged: boolean
  time_note: string
  /** Statuses Remind pre-selects; empty = every status. */
  remind_statuses: string[]
  customOpen: boolean
}
let nextKey = 1
const blankRow = (): Row => ({ key: nextKey++, activity: '', start_date: '', end_date: '', ranged: false, time_note: '', remind_statuses: [], customOpen: false })

const form = reactive({ timeline_name: '', ao_unit: '', irb_cycle: '', is_active: true, notes: '', showNotes: false, rows: [] as Row[] })
const saving = ref(false)
const error = ref('')
const touched = ref(false)
const confirmDiscard = ref(false)
let snapshot = ''

function serialize() {
  return JSON.stringify({
    n: form.timeline_name.trim(),
    u: form.ao_unit,
    c: form.irb_cycle.trim(),
    a: form.is_active,
    no: form.notes.trim(),
    r: filledRows.value.map((r) => [r.name, r.activity.trim(), r.start_date, r.ranged ? r.end_date : '', r.time_note.trim(), r.remind_statuses]),
  })
}
const dirty = computed(() => props.modelValue && serialize() !== snapshot)

const unitOptions = computed(() => [
  { label: 'All units', value: '' },
  ...props.units.map((u) => ({ label: `${u.path}  ·  ${u.ao_type}`, value: u.name })),
])

// ---------------------------------------------------------------- rows
/** The one activity being edited; the others show as compact timeline lines. */
const expandedKey = ref<number | null>(null)
function expand(r: Row) {
  collapseEmpty()
  expandedKey.value = r.key
  nextTick(() => document.getElementById(`tl-activity-${r.key}`)?.focus())
}
/** Closing an activity the admin never filled in just drops it. */
function collapseEmpty() {
  const open = form.rows.find((r) => r.key === expandedKey.value)
  if (open && !isFilled(open)) form.rows = form.rows.filter((r) => r !== open)
  expandedKey.value = null
}
function addRow() {
  const r = blankRow()
  collapseEmpty()
  form.rows.push(r)
  expand(r)
}
function removeRow(i: number) {
  if (form.rows[i]?.key === expandedKey.value) expandedKey.value = null
  form.rows.splice(i, 1)
}
function move(i: number, d: -1 | 1) {
  const j = i + d
  if (j < 0 || j >= form.rows.length) return
  const [r] = form.rows.splice(i, 1)
  form.rows.splice(j, 0, r)
}
function sortByDate() {
  form.rows.sort((a, b) => (a.start_date || '9999').localeCompare(b.start_date || '9999'))
}
function setRanged(r: Row, on: boolean) {
  r.ranged = on
  if (on && !r.end_date) r.end_date = r.start_date
  if (!on) r.end_date = ''
}

// ---------------------------------------------------------------- remind chips
const groups = computed(() => groupsFor(props.statuses))
const isAll = (r: Row) => !r.remind_statuses.length
const groupOn = (r: Row, g: StatusGroup) => !isAll(r) && g.statuses.every((s) => r.remind_statuses.includes(s))
function isCustom(r: Row) {
  if (isAll(r)) return false
  const covered = new Set(groups.value.filter((g) => groupOn(r, g)).flatMap((g) => g.statuses))
  return r.remind_statuses.some((s) => !covered.has(s))
}
function commit(r: Row, sel: Set<string>) {
  const list = props.statuses.filter((s) => sel.has(s))
  // Every status (or none) ticked both mean "all students".
  r.remind_statuses = list.length === props.statuses.length ? [] : list
}
function setAll(r: Row) {
  r.remind_statuses = []
  r.customOpen = false
}
function toggleGroup(r: Row, g: StatusGroup) {
  const sel = new Set(r.remind_statuses)
  const on = groupOn(r, g)
  for (const s of g.statuses) on ? sel.delete(s) : sel.add(s)
  commit(r, sel)
}
function toggleStatus(r: Row, s: string) {
  const sel = new Set(r.remind_statuses)
  sel.has(s) ? sel.delete(s) : sel.add(s)
  commit(r, sel)
}
function remindSummary(r: Row) {
  if (isAll(r)) return 'Remind targets every student in the timeline.'
  return `Remind pre-selects ${r.remind_statuses.length} status${r.remind_statuses.length === 1 ? '' : 'es'}.`
}

// ---------------------------------------------------------------- dates
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
function fmtLong(d: string) {
  const [y, m, day] = d.split('-').map(Number)
  if (!y || !m || !day) return ''
  return `${WEEKDAYS[new Date(Date.UTC(y, m - 1, day)).getUTCDay()]}, ${day} ${MONTHS[m - 1]} ${y}`
}
function dateHint(r: Row) {
  if (!r.start_date) return ''
  const due = r.ranged && r.end_date ? r.end_date : r.start_date
  const days = daysBetween(props.serverNow, due)
  // daysBetween(now, due) > 0 means the date is ahead: relativeDays(-n) = "in n days".
  const when = days === null ? '' : ` · ${relativeDays(-days)}`
  if (r.ranged && r.end_date && r.end_date !== r.start_date) return `${fmtLong(r.start_date)} → ${fmtLong(r.end_date)}${when}`
  return `${fmtLong(r.start_date)}${when}`
}
function fmtParsed(p: ParsedActivity) {
  if (!p.start_date) return ''
  return p.end_date ? `${fmtLong(p.start_date)} → ${fmtLong(p.end_date)}` : fmtLong(p.start_date)
}

// ---------------------------------------------------------------- validation
const isFilled = (r: Row) => !!(r.activity.trim() || r.start_date || r.end_date || r.time_note.trim())
const filledRows = computed(() => form.rows.filter(isFilled))
function rowError(r: Row) {
  if (!isFilled(r)) return ''
  if (!r.activity.trim()) return 'Enter the activity.'
  if (!r.start_date) return 'Pick the date.'
  if (r.ranged && !r.end_date) return "Pick the 'to' date, or untick 'Ends on a later date'."
  if (r.ranged && r.end_date < r.start_date) return "The 'to' date is before the start."
  return ''
}
/** Earlier than the activity above: almost always a typo (e.g. the wrong year). */
function rowWarning(r: Row, i: number) {
  const prev = form.rows.slice(0, i).reverse().find((x) => x.start_date)
  return prev && r.start_date && r.start_date < prev.start_date ? `This is earlier than the activity above (${fmtLong(prev.start_date)}). Check the year?` : ''
}
const problem = computed(() => {
  if (!form.timeline_name.trim()) return 'Give the timeline a name.'
  if (!filledRows.value.length) return 'Add at least one activity.'
  const i = form.rows.findIndex((r) => rowError(r))
  return i >= 0 ? `Activity ${i + 1}: ${rowError(form.rows[i])}` : ''
})

async function save() {
  touched.value = true
  confirmDiscard.value = false
  if (saving.value) return
  if (problem.value) {
    // Shown live from `problem` (see the template), so it clears itself once fixed.
    error.value = ''
    const bad = form.rows.find((r) => rowError(r))
    if (bad) {
      expandedKey.value = bad.key
      nextTick(() => document.getElementById(`tl-row-${bad.key}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' }))
    }
    else document.getElementById('tl-name')?.focus()
    return
  }
  saving.value = true
  error.value = ''
  try {
    const name = await saveTimeline({
      name: props.timeline?.name,
      timeline_name: form.timeline_name.trim(),
      ao_unit: form.ao_unit || null,
      irb_cycle: form.irb_cycle.trim() || null,
      is_active: form.is_active ? 1 : 0,
      notes: form.notes.trim() || null,
      milestones: filledRows.value.map((r) => ({
        name: r.name,
        activity: r.activity.trim(),
        start_date: r.start_date,
        end_date: r.ranged && r.end_date && r.end_date !== r.start_date ? r.end_date : null,
        time_note: r.time_note.trim() || null,
        remind_statuses: r.remind_statuses,
      })),
    })
    snapshot = serialize()
    emit('update:modelValue', false)
    emit('saved', name)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not save the timeline.'
  } finally {
    saving.value = false
  }
}

// Closing with unsaved edits (overlay click, Esc, Cancel) asks first.
function setOpen(v: boolean) {
  if (saving.value) return
  if (!v && dirty.value) {
    confirmDiscard.value = true
    return
  }
  emit('update:modelValue', v)
}
function discard() {
  confirmDiscard.value = false
  emit('update:modelValue', false)
}

// ---------------------------------------------------------------- paste from a document
const paste = reactive({ open: false, text: '', loading: false, error: '', rows: null as ParsedActivity[] | null, title: null as string | null })
function openPaste() {
  paste.open = true
  paste.rows = null
  paste.error = ''
  nextTick(() => document.getElementById('tl-paste')?.focus())
}
async function readPaste() {
  if (!paste.text.trim() || paste.loading) return
  paste.loading = true
  paste.error = ''
  try {
    const r = await parseActivities(paste.text)
    paste.rows = r.rows
    paste.title = r.title
    if (!r.rows.length) paste.error = 'No activities found. Copy the rows of the table (Activity and Dates columns) and paste again.'
  } catch (e) {
    paste.error = e instanceof Error ? e.message : 'Could not read the pasted text.'
  } finally {
    paste.loading = false
  }
}
function addParsed(replace: boolean) {
  if (!paste.rows?.length) return
  const added: Row[] = paste.rows.map((p) => ({
    key: nextKey++,
    activity: p.activity,
    start_date: p.start_date || '',
    end_date: p.end_date || '',
    ranged: !!p.end_date,
    time_note: p.time_note || '',
    remind_statuses: [],
    customOpen: false,
  }))
  form.rows = [...(replace ? [] : form.rows.filter(isFilled)), ...added]
  if (!form.timeline_name.trim() && paste.title) form.timeline_name = paste.title
  paste.open = false
  paste.text = ''
  paste.rows = null
  touched.value = added.some((r) => !r.start_date) // show which rows still need a date
  expandedKey.value = added.find((r) => !r.start_date)?.key ?? null
}
// ---------------------------------------------------------------- compact line helpers
function badge(d: string) {
  const [y, m, day] = d.split('-').map(Number)
  return y && m && day ? { day: String(day).padStart(2, '0'), mon: MONTHS[m - 1].toUpperCase(), year: y } : null
}
function whoShort(r: Row) {
  if (isAll(r)) return 'All students'
  const on = groups.value.filter((g) => groupOn(r, g))
  return isCustom(r) || !on.length ? `${r.remind_statuses.length} statuses` : on.map((g) => g.label).join(', ')
}
const span = computed(() => {
  const dates = filledRows.value.flatMap((r) => [r.start_date, r.ranged ? r.end_date : '']).filter(Boolean).sort()
  if (!dates.length) return ''
  const a = fmtLong(dates[0]).replace(/^\w+, /, '')
  const b = fmtLong(dates[dates.length - 1]).replace(/^\w+, /, '')
  return a === b ? a : `${a} → ${b}`
})
const parsedProblems = computed(() => (paste.rows ?? []).filter((r) => r.problem).length)

// Declared last: it resets everything above (paste panel, rows, snapshot).
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    const t = props.timeline
    error.value = ''
    touched.value = false
    confirmDiscard.value = false
    paste.open = false
    paste.rows = null
    form.timeline_name = t?.timeline_name ?? ''
    form.ao_unit = t?.ao_unit ?? ''
    form.irb_cycle = t?.irb_cycle ?? ''
    form.is_active = t ? !!t.is_active : true
    form.notes = t?.notes ?? ''
    form.showNotes = !!t?.notes
    form.rows = t?.milestones.length
      ? t.milestones.map((m) => ({
          key: nextKey++,
          name: m.name,
          activity: m.activity,
          start_date: m.start_date.slice(0, 10),
          end_date: (m.end_date || '').slice(0, 10),
          ranged: !!m.end_date,
          time_note: m.time_note || '',
          remind_statuses: [...m.remind_statuses],
          customOpen: false,
        }))
      : [] // a new timeline starts on the "paste or add" empty state
    expandedKey.value = null
    await nextTick()
    snapshot = serialize()
  },
  { immediate: true },
)

const inputCls =
  'h-8 w-full rounded-md border border-line bg-paper px-2.5 text-sm text-charcoal placeholder:text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20'
const chipCls = (on: boolean) =>
  `rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors ${on ? 'border-primary bg-primary text-white' : 'border-line bg-paper text-charcoal hover:border-primary'}`
</script>


<template>
  <Dialog :model-value="modelValue" :options="{ size: '4xl' }" @update:model-value="setOpen">
    <template #body>
      <div class="flex max-h-[88vh] flex-col bg-paper">
        <!-- header -->
        <header class="flex items-start justify-between gap-4 border-b border-line px-6 py-4">
          <div class="flex items-center gap-3">
            <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white"><FeatherIcon name="calendar" class="h-5 w-5" /></span>
            <div>
              <h2 class="text-lg font-semibold text-charcoal">{{ timeline ? 'Edit timeline' : 'New timeline' }}</h2>
              <p class="text-xs text-muted">The IRB calendar a school publishes for a cycle.</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <label class="flex cursor-pointer items-center gap-2 rounded-full border border-line px-3 py-1.5 text-xs font-medium" :title="'Scheduled reminders only go out while the timeline is active. “Send now” always works.'">
              <Switch v-model="form.is_active" aria-label="Active" />
              <span :class="form.is_active ? 'text-success' : 'text-muted'">{{ form.is_active ? 'Active' : 'Inactive' }}</span>
            </label>
            <button type="button" class="rounded-md p-1.5 text-muted hover:bg-canvas hover:text-charcoal" aria-label="Close" @click="setOpen(false)">
              <FeatherIcon name="x" class="h-5 w-5" />
            </button>
          </div>
        </header>

        <form class="flex-1 space-y-7 overflow-y-auto px-6 py-5 sirb-scrollbar" @submit.prevent="save">
          <!-- details -->
          <section class="space-y-4">
            <div>
              <label for="tl-name" class="mb-1.5 block text-sm font-medium text-charcoal">Timeline name <span class="text-danger">*</span></label>
              <input id="tl-name" v-model="form.timeline_name" type="text" placeholder="e.g. School of Development – August 2026" :class="inputCls + ' h-10 text-base'" />
              <p v-if="touched && !form.timeline_name.trim()" class="mt-1 text-xs text-danger">Give the timeline a name.</p>
            </div>
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="sirb-fill-select sirb-truncate-select">
                <FormControl v-model="form.ao_unit" type="select" label="Applies to" :options="unitOptions" />
                <p class="mt-1 text-xs text-muted">Students of this unit and everything under it.</p>
              </div>
              <div>
                <label for="tl-cycle" class="mb-1.5 block text-xs text-ink-gray-5">IRB cycle</label>
                <input id="tl-cycle" v-model="form.irb_cycle" list="tl-cycles" type="text" placeholder="Every cycle" :class="inputCls" />
                <datalist id="tl-cycles"><option v-for="c in cycles" :key="c" :value="c" /></datalist>
                <p class="mt-1 text-xs text-muted">Only projects in this cycle. Empty = every cycle.</p>
              </div>
            </div>
            <div>
              <button v-if="!form.showNotes" type="button" class="flex items-center gap-1 text-sm font-medium text-muted hover:text-charcoal" @click="form.showNotes = true">
                <FeatherIcon name="plus" class="h-3.5 w-3.5" /> Add a note
              </button>
              <FormControl v-else v-model="form.notes" type="textarea" label="Note" :rows="2" placeholder="Anything the IRB office should know about this timeline" />
            </div>
          </section>

          <!-- activities -->
          <section>
            <div class="mb-3 flex flex-wrap items-end justify-between gap-3 border-b border-line pb-3">
              <div>
                <h3 class="text-base font-semibold text-charcoal">Activities</h3>
                <p class="text-xs text-muted">
                  <template v-if="filledRows.length">{{ filledRows.length }} activit{{ filledRows.length === 1 ? 'y' : 'ies' }}<template v-if="span"> · {{ span }}</template></template>
                  <template v-else>Each row of your timeline table, with its date.</template>
                </p>
              </div>
              <div v-if="form.rows.length" class="flex gap-2">
                <Button variant="ghost" size="sm" icon-left="clipboard" @click="openPaste">Paste</Button>
                <Button variant="ghost" size="sm" icon-left="arrow-down" :disabled="filledRows.length < 2" @click="sortByDate">Sort by date</Button>
                <Button variant="outline" size="sm" icon-left="plus" @click="addRow">Add activity</Button>
              </div>
            </div>

            <!-- paste panel -->
            <div v-if="paste.open" class="mb-4 rounded-xl border border-line bg-canvas p-4">
              <template v-if="!paste.rows?.length">
                <div class="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <label for="tl-paste" class="block text-sm font-semibold text-charcoal">Paste your timeline table</label>
                    <p class="text-xs text-muted">Select the table rows in Word or Excel, copy (Ctrl+C) and paste here (Ctrl+V). Dates like “25th July to 5th August” are understood.</p>
                  </div>
                  <button type="button" class="rounded p-1 text-muted hover:text-charcoal" aria-label="Close paste" @click="paste.open = false"><FeatherIcon name="x" class="h-4 w-4" /></button>
                </div>
                <textarea
                  id="tl-paste"
                  v-model="paste.text"
                  rows="6"
                  class="w-full rounded-lg border border-line bg-paper px-3 py-2 font-mono text-xs text-charcoal focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20"
                  placeholder="Activity&#9;Dates&#10;Last date for submission of IRB forms&#9;25th July 2026"
                />
                <p v-if="paste.error" class="mt-1 text-xs text-danger">{{ paste.error }}</p>
                <div class="mt-3 flex justify-end">
                  <Button variant="solid" size="sm" icon-left="zap" :loading="paste.loading" :disabled="!paste.text.trim()" @click="readPaste">Read activities</Button>
                </div>
              </template>
              <template v-else>
                <div class="mb-2 flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-charcoal">
                      Found {{ paste.rows.length }} activit{{ paste.rows.length === 1 ? 'y' : 'ies' }}<template v-if="paste.title"> · “{{ paste.title }}”</template>
                    </p>
                    <p class="text-xs" :class="parsedProblems ? 'text-warning' : 'text-muted'">
                      {{ parsedProblems ? `${parsedProblems} need a date filled in after adding.` : 'Looks good — add them to the timeline.' }}
                    </p>
                  </div>
                </div>
                <ol class="max-h-60 divide-y divide-line overflow-y-auto rounded-lg border border-line bg-paper sirb-scrollbar">
                  <li v-for="(p, i) in paste.rows" :key="i" class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 px-3 py-2 text-sm">
                    <span class="w-5 shrink-0 text-xs text-muted">{{ i + 1 }}</span>
                    <span class="min-w-0 flex-1 text-charcoal">{{ p.activity }}</span>
                    <span v-if="p.start_date" class="whitespace-nowrap text-xs text-charcoal">{{ fmtParsed(p) }}</span>
                    <span v-if="p.time_note" class="whitespace-nowrap text-xs text-muted">{{ p.time_note }}</span>
                    <span v-if="p.problem" class="flex items-center gap-1 whitespace-nowrap text-xs text-warning"><FeatherIcon name="alert-triangle" class="h-3 w-3" />{{ p.problem }}</span>
                  </li>
                </ol>
                <div class="mt-3 flex flex-wrap justify-end gap-2">
                  <Button variant="ghost" size="sm" @click="paste.rows = null">Back</Button>
                  <Button v-if="filledRows.length" variant="outline" size="sm" @click="addParsed(true)">Replace the {{ filledRows.length }} current</Button>
                  <Button variant="solid" size="sm" icon-left="plus" @click="addParsed(false)">
                    {{ filledRows.length ? 'Add to the list' : `Add ${paste.rows.length} activit${paste.rows.length === 1 ? 'y' : 'ies'}` }}
                  </Button>
                </div>
              </template>
            </div>

            <!-- empty state -->
            <div v-if="!form.rows.length && !paste.open" class="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                class="group flex items-start gap-3 rounded-xl border-2 border-dashed border-line p-5 text-left transition-colors hover:border-primary hover:bg-canvas"
                @click="openPaste"
              >
                <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white"><FeatherIcon name="clipboard" class="h-5 w-5" /></span>
                <span>
                  <span class="block text-sm font-semibold text-charcoal">Paste from your document</span>
                  <span class="block text-xs text-muted">Copy the timeline table from Word or Excel — the activities and dates are filled in for you.</span>
                </span>
              </button>
              <button
                type="button"
                class="group flex items-start gap-3 rounded-xl border-2 border-dashed border-line p-5 text-left transition-colors hover:border-primary hover:bg-canvas"
                @click="addRow"
              >
                <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-canvas text-charcoal group-hover:bg-primary group-hover:text-white"><FeatherIcon name="plus" class="h-5 w-5" /></span>
                <span>
                  <span class="block text-sm font-semibold text-charcoal">Add activities one by one</span>
                  <span class="block text-xs text-muted">Type each activity and pick its date.</span>
                </span>
              </button>
            </div>

            <!-- the timeline -->
            <ol v-else-if="form.rows.length" class="relative">
              <li
                v-for="(r, i) in form.rows"
                :id="`tl-row-${r.key}`"
                :key="r.key"
                class="relative pb-3 pl-20 last:pb-0"
              >
                <!-- rail + date badge -->
                <span v-if="i < form.rows.length - 1" class="absolute left-[1.9rem] top-12 bottom-0 w-px bg-line" aria-hidden="true" />
                <span
                  class="absolute left-0 top-1 flex w-[3.8rem] flex-col items-center rounded-lg border py-1.5 text-center leading-none"
                  :class="touched && rowError(r) ? 'border-red-300 bg-red-50' : r.key === expandedKey ? 'border-primary bg-primary text-white' : 'border-line bg-paper'"
                >
                  <template v-if="badge(r.start_date)">
                    <span class="text-lg font-bold" :class="r.key === expandedKey ? 'text-white' : 'text-charcoal'">{{ badge(r.start_date)!.day }}</span>
                    <span class="mt-0.5 text-[10px] font-semibold tracking-wider" :class="r.key === expandedKey ? 'text-white/80' : 'text-muted'">{{ badge(r.start_date)!.mon }}</span>
                    <span class="mt-0.5 text-[10px]" :class="r.key === expandedKey ? 'text-white/70' : 'text-muted'">{{ badge(r.start_date)!.year }}</span>
                  </template>
                  <FeatherIcon v-else name="calendar" class="my-2 h-4 w-4" :class="r.key === expandedKey ? 'text-white' : 'text-muted'" />
                </span>

                <!-- collapsed line -->
                <div
                  v-if="r.key !== expandedKey"
                  role="button"
                  tabindex="0"
                  class="group flex items-start gap-3 rounded-xl border bg-paper px-4 py-3 transition-shadow hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                  :class="touched && rowError(r) ? 'border-red-300' : 'border-line'"
                  :aria-label="`Edit activity ${i + 1}`"
                  @click="expand(r)"
                  @keydown.enter.prevent="expand(r)"
                >
                  <div class="min-w-0 flex-1">
                    <p class="text-sm font-medium" :class="r.activity.trim() ? 'text-charcoal' : 'italic text-muted'">{{ r.activity.trim() || 'Untitled activity' }}</p>
                    <p class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                      <span v-if="r.start_date">{{ dateHint(r) }}</span>
                      <span v-else class="text-danger">No date yet</span>
                      <span v-if="r.time_note.trim()">· {{ r.time_note }}</span>
                      <span class="rounded-full bg-canvas px-2 py-0.5 text-[11px] font-medium text-charcoal"><FeatherIcon name="bell" class="-mt-0.5 mr-0.5 inline h-3 w-3" />{{ whoShort(r) }}</span>
                    </p>
                    <p v-if="touched && rowError(r)" class="mt-1 text-xs text-danger">{{ rowError(r) }}</p>
                    <p v-else-if="rowWarning(r, i)" class="mt-1 flex items-center gap-1 text-xs text-warning"><FeatherIcon name="alert-triangle" class="h-3 w-3" />{{ rowWarning(r, i) }}</p>
                  </div>
                  <div class="flex shrink-0 items-center gap-0.5 opacity-60 transition-opacity group-hover:opacity-100" @click.stop>
                    <button type="button" class="rounded p-1 text-muted hover:bg-canvas disabled:opacity-30" :disabled="i === 0" :aria-label="`Move activity ${i + 1} up`" @click="move(i, -1)"><FeatherIcon name="chevron-up" class="h-4 w-4" /></button>
                    <button type="button" class="rounded p-1 text-muted hover:bg-canvas disabled:opacity-30" :disabled="i === form.rows.length - 1" :aria-label="`Move activity ${i + 1} down`" @click="move(i, 1)"><FeatherIcon name="chevron-down" class="h-4 w-4" /></button>
                    <button type="button" class="rounded p-1 text-muted hover:bg-canvas hover:text-danger" :aria-label="`Remove activity ${i + 1}`" @click="removeRow(i)"><FeatherIcon name="trash-2" class="h-4 w-4" /></button>
                  </div>
                </div>

                <!-- expanded editor -->
                <div v-else class="rounded-xl border-2 border-primary bg-paper p-4 shadow-sm">
                  <input
                    :id="`tl-activity-${r.key}`"
                    v-model="r.activity"
                    type="text"
                    placeholder="Activity, e.g. Last date for submission of IRB forms"
                    :aria-label="`Activity ${i + 1}`"
                    :class="inputCls + ' h-10 text-base font-medium'"
                    @keydown.enter.prevent="collapseEmpty()"
                  />
                  <div class="mt-4 grid gap-4 sm:grid-cols-[11rem_11rem_minmax(0,1fr)]">
                    <div>
                      <label :for="`tl-date-${r.key}`" class="mb-1 block text-xs font-medium text-muted">{{ r.ranged ? 'From' : 'Date' }}</label>
                      <input :id="`tl-date-${r.key}`" v-model="r.start_date" type="date" :aria-label="`Date ${i + 1}`" :class="inputCls" />
                    </div>
                    <div>
                      <label class="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
                        <input
                          type="checkbox"
                          class="h-3.5 w-3.5 rounded border-gray-300 text-primary focus:ring-primary"
                          :checked="r.ranged"
                          :aria-label="`Activity ${i + 1} ends on a later date`"
                          @change="setRanged(r, ($event.target as HTMLInputElement).checked)"
                        />
                        Ends on a later date
                      </label>
                      <input v-if="r.ranged" v-model="r.end_date" type="date" :min="r.start_date || undefined" :aria-label="`To ${i + 1}`" :class="inputCls" />
                      <p v-else class="pt-1.5 text-xs text-muted">Single day</p>
                    </div>
                    <div>
                      <label :for="`tl-note-${r.key}`" class="mb-1 block text-xs font-medium text-muted">Time / note</label>
                      <input :id="`tl-note-${r.key}`" v-model="r.time_note" type="text" placeholder="e.g. 6:00 PM, or 2–4 pm" :aria-label="`Note ${i + 1}`" :class="inputCls" />
                    </div>
                  </div>
                  <p v-if="dateHint(r)" class="mt-2 text-xs text-muted"><FeatherIcon name="calendar" class="-mt-0.5 mr-1 inline h-3 w-3" />{{ dateHint(r) }}</p>

                  <div class="mt-4 border-t border-line pt-3">
                    <p class="mb-2 text-xs font-medium text-muted">Who Remind targets</p>
                    <div class="flex flex-wrap gap-1.5">
                      <button type="button" :class="chipCls(isAll(r))" @click="setAll(r)">All students</button>
                      <button v-for="g in groups" :key="g.key" type="button" :class="chipCls(groupOn(r, g))" :title="g.hint" @click="toggleGroup(r, g)">{{ g.label }}</button>
                      <button type="button" :class="chipCls(isCustom(r) || r.customOpen)" :aria-expanded="r.customOpen" @click="r.customOpen = !r.customOpen">Custom…</button>
                    </div>
                    <p class="mt-1.5 text-xs text-muted">{{ remindSummary(r) }}</p>
                    <div v-if="r.customOpen" class="mt-2 grid gap-3 rounded-lg border border-line bg-canvas p-3 sm:grid-cols-2">
                      <div v-for="g in groups" :key="g.key">
                        <p class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted">{{ g.label }}</p>
                        <label v-for="s in g.statuses" :key="s" class="flex cursor-pointer items-start gap-2 py-0.5 text-xs text-charcoal">
                          <input type="checkbox" class="mt-0.5 h-3.5 w-3.5 rounded border-gray-300 text-primary focus:ring-primary" :checked="r.remind_statuses.includes(s)" @change="toggleStatus(r, s)" />
                          {{ s }}
                        </label>
                      </div>
                    </div>
                  </div>

                  <p v-if="touched && rowError(r)" class="mt-3 flex items-center gap-1.5 text-xs text-danger"><FeatherIcon name="alert-circle" class="h-3.5 w-3.5" />{{ rowError(r) }}</p>
                  <p v-else-if="rowWarning(r, i)" class="mt-3 flex items-center gap-1.5 text-xs text-warning"><FeatherIcon name="alert-triangle" class="h-3.5 w-3.5" />{{ rowWarning(r, i) }}</p>

                  <div class="mt-4 flex items-center justify-between">
                    <button type="button" class="flex items-center gap-1 text-xs font-medium text-muted hover:text-danger" :aria-label="`Remove activity ${i + 1}`" @click="removeRow(i)">
                      <FeatherIcon name="trash-2" class="h-3.5 w-3.5" /> Remove
                    </button>
                    <Button size="sm" variant="solid" icon-left="check" @click="collapseEmpty()">Done</Button>
                  </div>
                </div>
              </li>
            </ol>
          </section>

          <p v-if="(touched && problem) || error" class="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger">{{ (touched && problem) || error }}</p>
          <button type="submit" class="hidden" />
        </form>

        <!-- footer -->
        <footer class="border-t border-line bg-canvas px-6 py-3">
          <div v-if="confirmDiscard" class="flex flex-wrap items-center justify-between gap-3">
            <p class="flex items-center gap-2 text-sm text-charcoal"><FeatherIcon name="alert-triangle" class="h-4 w-4 text-warning" />You have unsaved changes. Discard them?</p>
            <div class="flex gap-2">
              <Button variant="outline" @click="confirmDiscard = false">Keep editing</Button>
              <Button variant="solid" theme="red" @click="discard">Discard</Button>
            </div>
          </div>
          <div v-else class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-xs text-muted">
              <template v-if="touched && problem">{{ problem }}</template>
              <template v-else-if="filledRows.length">{{ filledRows.length }} activit{{ filledRows.length === 1 ? 'y' : 'ies' }} ready</template>
            </p>
            <div class="flex gap-2">
              <Button variant="outline" :disabled="saving" @click="setOpen(false)">Cancel</Button>
              <Button variant="solid" :loading="saving" icon-left="check" @click="save">{{ timeline ? 'Save changes' : 'Create timeline' }}</Button>
            </div>
          </div>
        </footer>
      </div>
    </template>
  </Dialog>
</template>
