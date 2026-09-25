<script setup lang="ts">
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import { Button, Dialog, FeatherIcon, FormControl } from 'frappe-ui'
import StatusChecklist from './StatusChecklist.vue'
import StudentPicker from './StudentPicker.vue'
import RecipientList from './RecipientList.vue'
import { fetchStudentLabels, previewEmail, previewRecipients, saveAlert, sendNow } from '@/services/alerts'
import type {
  AlertEnvironment,
  AlertFilters,
  AlertFrequency,
  EmailPreview,
  EmailTemplateOption,
  IrbTimeline,
  RecipientPreview,
  StudentOption,
  TimelineAlert,
  TimelineMilestone,
} from '@/types/alerts'
import { cleanFilters } from '@/utils/alertFilters'
import type { serverClock } from '@/utils/serverTime'
import { toDateTimeInput } from '@/utils/serverTime'

/**
 * Remind the students of one timeline activity: choose who, check the
 * e-mail, then send it now or schedule it relative to the deadline.
 * Recipients always follow the timeline's current unit and cycle (the
 * server applies them), so only statuses / picked students are stored.
 */
const props = defineProps<{
  modelValue: boolean
  timeline: IrbTimeline | null
  milestone: TimelineMilestone | null
  /** A scheduled reminder being edited, or null for a new one. */
  alert: TimelineAlert | null
  templates: EmailTemplateOption[]
  statuses: string[]
  env: AlertEnvironment
  clock: ReturnType<typeof serverClock>
}>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; sent: []; saved: [] }>()

const DEADLINE_TEMPLATE = 'Timeline Alert - Deadline Reminder'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// ---------------------------------------------------------------- state
type RecipientMode = 'status' | 'students'
const recipientMode = ref<RecipientMode>('status')
const statusSelection = ref<string[] | null>(null)
const picked = ref<StudentOption[]>([])
const template = ref('')
const whenMode = ref<'now' | 'schedule'>('schedule')
type PresetKey = 'w' | '3' | '1' | '0' | 'd' | 'custom'
const schedule = reactive({ choice: '1' as PresetKey, frequency: 'Once' as AlertFrequency, start_at: '', end_date: '' })
const name = ref('')
const nameTouched = ref(false)
const busy = ref(false)
const confirming = ref(false)
const error = ref('')
const showList = ref(false)
let openSeq = 0

const deadline = computed(() => (props.milestone ? (props.milestone.deadline || props.milestone.end_date || props.milestone.start_date).slice(0, 10) : ''))
const link = computed(() => (props.timeline && props.milestone?.name ? { timeline: props.timeline.name, milestone: props.milestone.name } : null))

function fmtDay(d: string) {
  const [y, m, day] = d.slice(0, 10).split('-').map(Number)
  return `${day} ${MONTHS[m - 1]} ${y}`
}
function fmtStart(v: string) {
  return v ? `${fmtDay(v)}, ${v.slice(11, 16)}` : ''
}

// ---------------------------------------------------------------- presets
function shiftDate(date: string, days: number) {
  const [y, m, d] = date.split('-').map(Number)
  const t = new Date(Date.UTC(y, m - 1, d + days))
  return `${t.getUTCFullYear()}-${String(t.getUTCMonth() + 1).padStart(2, '0')}-${String(t.getUTCDate()).padStart(2, '0')}`
}
const PRESETS: { key: Exclude<PresetKey, 'custom'>; label: string; days: number; daily: boolean }[] = [
  { key: 'w', label: '1 week before', days: 7, daily: false },
  { key: '3', label: '3 days before', days: 3, daily: false },
  { key: '1', label: '1 day before', days: 1, daily: false },
  { key: '0', label: 'On the day', days: 0, daily: false },
  { key: 'd', label: 'Daily for the last week', days: 7, daily: true },
]
const presetStart = (p: (typeof PRESETS)[number]) => `${shiftDate(deadline.value, -p.days)}T09:00`
function presetDisabled(p: (typeof PRESETS)[number]) {
  if (!deadline.value) return true
  const now = props.clock.input()
  return p.daily ? `${deadline.value}T23:59` <= now : presetStart(p) <= now
}
function applyPreset(key: PresetKey) {
  schedule.choice = key
  const p = PRESETS.find((x) => x.key === key)
  if (!p) return // custom keeps the current values
  if (p.daily) {
    const start = presetStart(p)
    schedule.frequency = 'Daily'
    schedule.start_at = start > props.clock.input() ? start : props.clock.nextHourInput()
    schedule.end_date = deadline.value
  } else {
    schedule.frequency = 'Once'
    schedule.start_at = presetStart(p)
    schedule.end_date = ''
  }
  if (!nameTouched.value) name.value = `${p.label} – ${props.milestone?.activity ?? ''}`.slice(0, 140)
}
function onRepeatChange(v: AlertFrequency) {
  schedule.frequency = v
  if (v !== 'Once' && !schedule.end_date) schedule.end_date = deadline.value
}

// ---------------------------------------------------------------- recipients
const pickEmpty = computed(() => recipientMode.value === 'students' && !picked.value.length)
const statusNone = computed(() => statusSelection.value !== null && !statusSelection.value.length)
const filters = computed<AlertFilters>(() => {
  const base: AlertFilters =
    recipientMode.value === 'students' ? { mode: 'students', student: picked.value.map((s) => s.student) } : {}
  if (statusSelection.value?.length) base.status = [...statusSelection.value]
  return cleanFilters(base)
})
const key = computed(() => JSON.stringify([filters.value, statusNone.value, props.timeline?.name]))

const recipients = ref<RecipientPreview | null>(null)
const recipientsKey = ref('')
const recipientsLoading = ref(false)
const recipientsError = ref('')
let rSeq = 0
let rTimer: ReturnType<typeof setTimeout> | undefined
async function loadRecipients() {
  const k = key.value
  const mine = ++rSeq
  recipientsError.value = ''
  if (!props.modelValue || !props.timeline) return
  if (pickEmpty.value) {
    recipients.value = null
    recipientsKey.value = k
    recipientsLoading.value = false
    return
  }
  recipientsLoading.value = true
  try {
    const r = await previewRecipients(filters.value, props.timeline.name)
    if (mine !== rSeq) return
    recipients.value = statusNone.value
      ? { ...r, sendable_count: 0, skipped_count: 0, unique_students: 0, sendable: [], skipped: [] }
      : r
    recipientsKey.value = k
  } catch (e) {
    if (mine !== rSeq) return
    recipients.value = null
    recipientsError.value = e instanceof Error ? e.message : 'Could not load recipients.'
  } finally {
    if (mine === rSeq) recipientsLoading.value = false
  }
}
watch([key, () => props.modelValue], ([, open]) => {
  clearTimeout(rTimer)
  if (!open) return
  recipientsLoading.value = true
  rTimer = setTimeout(loadRecipients, 300)
}, { immediate: true })
const recipientsFresh = computed(() => !!recipients.value && recipientsKey.value === key.value && !recipientsLoading.value)

const scopeText = computed(() => {
  const t = props.timeline
  if (!t) return ''
  const unit = t.unit_name ? t.unit_name : 'every unit'
  return `Students of ${unit}${t.irb_cycle ? `, ${t.irb_cycle} cycle` : ''}`
})

// ---------------------------------------------------------------- e-mail preview
const templateOptions = computed(() => [
  { label: 'Select a template…', value: '' },
  ...props.templates.map((t) => ({ label: t.name, value: t.name })),
])
const preview = ref<EmailPreview | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
let pSeq = 0
let pTimer: ReturnType<typeof setTimeout> | undefined
async function loadPreview() {
  const mine = ++pSeq
  if (!props.modelValue || !template.value) {
    preview.value = null
    previewError.value = ''
    previewLoading.value = false
    return
  }
  previewLoading.value = true
  previewError.value = ''
  try {
    const p = await previewEmail(template.value, pickEmpty.value ? {} : filters.value, link.value)
    if (mine === pSeq) preview.value = p
  } catch (e) {
    if (mine !== pSeq) return
    preview.value = null
    previewError.value = e instanceof Error ? e.message : 'Could not render the template.'
  } finally {
    if (mine === pSeq) previewLoading.value = false
  }
}
watch([template, key, () => props.modelValue], ([, , open]) => {
  clearTimeout(pTimer)
  if (!open) return
  previewLoading.value = !!template.value
  pTimer = setTimeout(loadPreview, 300)
}, { immediate: true })
const unknownVariables = computed(() => preview.value?.unknown_variables ?? [])
const varToken = (n: string) => '{' + '{ ' + n + ' }' + '}'

// Templates are edited in Desk in another tab: re-render when coming back.
function onVisible() {
  if (document.visibilityState === 'visible' && props.modelValue && template.value) loadPreview()
}
document.addEventListener('visibilitychange', onVisible)
onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisible)
  clearTimeout(rTimer)
  clearTimeout(pTimer)
})

// ---------------------------------------------------------------- open / reset
watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    const mine = ++openSeq
    // Nothing from the previously opened activity may linger on screen.
    recipients.value = null
    recipientsKey.value = ''
    preview.value = null
    error.value = ''
    confirming.value = false
    showList.value = false
    busy.value = false
    nameTouched.value = false
    const a = props.alert
    template.value =
      a?.email_template ??
      (props.templates.some((t) => t.name === DEADLINE_TEMPLATE) ? DEADLINE_TEMPLATE : props.templates[0]?.name ?? '')
    if (a) {
      statusSelection.value = a.filters.status?.length ? [...a.filters.status] : null
      recipientMode.value = a.filters.mode === 'students' ? 'students' : 'status'
      picked.value = []
      whenMode.value = 'schedule'
      schedule.choice = 'custom'
      schedule.frequency = a.frequency
      schedule.start_at = toDateTimeInput(a.start_at)
      schedule.end_date = a.end_date ?? ''
      name.value = a.alert_name
      nameTouched.value = true
      if (a.filters.mode === 'students' && a.filters.student?.length) {
        const names = a.filters.student
        let rows: StudentOption[] = []
        try {
          rows = await fetchStudentLabels(names)
        } catch {
          error.value = 'Could not load the selected students.'
        }
        if (mine !== openSeq) return
        const byName = new Map(rows.map((r) => [r.student, r]))
        picked.value = names.map(
          (n) =>
            byName.get(n) ?? { student: n, student_name: `${n} (no current project)`, student_id: null, email: null, user_enabled: 0, programme: null, project_count: 0 },
        )
      }
    } else {
      statusSelection.value = props.milestone?.remind_statuses.length ? [...props.milestone.remind_statuses] : null
      recipientMode.value = 'status'
      picked.value = []
      name.value = ''
      // Default to a reminder the day before; once that's past, send now.
      const dayBefore = PRESETS[2]
      if (!presetDisabled(dayBefore)) {
        whenMode.value = 'schedule'
        applyPreset('1')
      } else {
        whenMode.value = 'now'
        schedule.choice = 'custom'
        schedule.frequency = 'Once'
        schedule.start_at = props.clock.nextHourInput()
        schedule.end_date = ''
        name.value = `Reminder – ${props.milestone?.activity ?? ''}`.slice(0, 140)
      }
    }
  },
  { immediate: true },
)

// ---------------------------------------------------------------- validation
const commonBlocker = computed(() => {
  if (pickEmpty.value) return 'Pick at least one student.'
  if (statusNone.value) return 'Tick at least one project status.'
  if (!template.value) return 'Choose an e-mail template.'
  if (previewLoading.value) return 'Checking the e-mail…'
  if (previewError.value) return 'Fix the template error first.'
  if (unknownVariables.value.length) return 'The template uses unknown variables. Fix them in the template first.'
  return ''
})
const sendBlocker = computed(() => {
  if (!props.env.email_configured) return 'No outgoing e-mail account is set up, so nothing can be sent yet.'
  if (commonBlocker.value) return commonBlocker.value
  if (!recipientsFresh.value) return 'Checking recipients…'
  if (!recipients.value?.sendable_count) return 'Nobody with an e-mail address matches.'
  return ''
})
// A function, not a computed: it compares against the clock.
function scheduleProblem() {
  if (commonBlocker.value) return commonBlocker.value
  if (!name.value.trim()) return 'Give the reminder a name.'
  if (!schedule.start_at) return 'Choose when to send it.'
  if (schedule.frequency === 'Once' && schedule.start_at <= props.clock.input()) return 'That time is in the past. Pick a later time, or send it now.'
  if (schedule.frequency !== 'Once' && schedule.end_date && schedule.end_date < schedule.start_at.slice(0, 10))
    return "'Until' is before the first reminder."
  return ''
}
const scheduleSummary = computed(() => {
  if (!schedule.start_at) return ''
  const at = schedule.start_at.slice(11, 16)
  if (schedule.frequency === 'Once') return `Once, on ${fmtStart(schedule.start_at)}`
  const until = schedule.end_date ? ` until ${fmtDay(schedule.end_date)}` : ''
  return `${schedule.frequency} at ${at}, from ${fmtDay(schedule.start_at)}${until}`
})
const emails = computed(() => (recipientsFresh.value ? recipients.value?.sendable_count ?? 0 : null))

// ---------------------------------------------------------------- actions
function newRequestId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}
let requestId = ''
function askSend() {
  if (sendBlocker.value) return
  error.value = ''
  // One id per confirmation: a double click or a retried request returns the same run.
  requestId = newRequestId()
  confirming.value = true
}
async function doSend() {
  if (busy.value || sendBlocker.value) return
  busy.value = true
  error.value = ''
  try {
    await sendNow(template.value, filters.value, requestId, link.value)
    emit('update:modelValue', false)
    emit('sent')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not send the reminder.'
    confirming.value = false
  } finally {
    busy.value = false
  }
}
async function doSchedule() {
  if (busy.value) return
  const problem = scheduleProblem()
  if (problem) {
    error.value = problem
    return
  }
  busy.value = true
  error.value = ''
  try {
    await saveAlert({
      name: props.alert?.name,
      alert_name: name.value.trim(),
      email_template: template.value,
      filters: filters.value,
      frequency: schedule.frequency,
      start_at: schedule.start_at,
      end_date: schedule.frequency === 'Once' ? null : schedule.end_date || null,
      enabled: props.alert ? props.alert.enabled : 1,
      timeline: link.value?.timeline ?? null,
      milestone: link.value?.milestone ?? null,
    })
    emit('update:modelValue', false)
    emit('saved')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not save the reminder.'
  } finally {
    busy.value = false
  }
}
function setOpen(v: boolean) {
  if (!busy.value) emit('update:modelValue', v)
}
const RECIPIENT_OPTIONS = [
  { v: 'status', l: 'By project status', i: 'filter', d: '' },
  { v: 'students', l: 'Specific students', i: 'user-check', d: 'Search by name, ID or e-mail and choose who gets it' },
] as const
const WHEN_OPTIONS = [
  { v: 'schedule', l: 'Schedule reminder', i: 'clock', d: 'Send automatically before the deadline' },
  { v: 'now', l: 'Send now', i: 'send', d: 'E-mail the students right away' },
] as const
const optionCls = (on: boolean) =>
  `flex w-full items-start gap-3 rounded-lg border-2 px-4 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
    on ? 'border-primary bg-paper shadow-sm' : 'border-line bg-canvas hover:border-gray-400'
  }`
const iconCls = (on: boolean) =>
  `flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${on ? 'bg-primary text-white' : 'bg-paper text-muted'}`
const inputCls =
  'h-7 w-full rounded border border-line bg-canvas px-2 text-sm text-charcoal focus:border-primary focus:outline-none focus:ring-0'
</script>

<template>
  <Dialog :model-value="modelValue" :options="{ title: alert ? 'Edit reminder' : 'Remind students', size: '5xl' }" @update:model-value="setOpen">
    <template #body-content>
      <div v-if="timeline && milestone" class="space-y-6">
        <!-- the activity -->
        <div class="flex flex-wrap items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
          <FeatherIcon name="calendar" class="mt-0.5 h-4 w-4 shrink-0 text-info" />
          <div class="min-w-0">
            <p class="font-medium text-charcoal">{{ milestone.activity }}</p>
            <p class="text-sm text-muted">
              Due {{ fmtDay(deadline) }}{{ milestone.time_note ? ` · ${milestone.time_note}` : '' }} · {{ timeline.timeline_name }}
            </p>
          </div>
        </div>

        <!-- 1. who -->
        <section>
          <h3 class="mb-2 flex items-center gap-2 text-sm font-semibold text-charcoal">
            <span class="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] text-white">1</span>
            Who gets it
          </h3>
          <div class="mb-3 grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="Who gets it">
            <button
              v-for="m in RECIPIENT_OPTIONS"
              :key="m.v"
              type="button"
              role="radio"
              :aria-checked="recipientMode === m.v"
              :class="optionCls(recipientMode === m.v)"
              @click="recipientMode = m.v"
            >
              <span :class="iconCls(recipientMode === m.v)"><FeatherIcon :name="m.i" class="h-4 w-4" /></span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-semibold text-charcoal">{{ m.l }}</span>
                <span class="block text-xs text-muted">{{ m.v === 'status' ? `${scopeText}, by project status (from the timeline)` : m.d }}</span>
              </span>
              <FeatherIcon v-if="recipientMode === m.v" name="check-circle" class="h-4 w-4 shrink-0 text-primary" />
            </button>
          </div>
          <StudentPicker v-if="recipientMode === 'students'" v-model="picked" class="mb-3" />
          <StatusChecklist
            v-model="statusSelection"
            :statuses="statuses"
            :counts="pickEmpty ? null : recipients?.status_counts ?? null"
            :loading="recipientsLoading"
          />
          <div class="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-canvas px-4 py-2.5 text-sm">
            <span class="flex items-center gap-2">
              <FeatherIcon :name="recipientsLoading ? 'loader' : 'users'" class="h-4 w-4 text-muted" :class="recipientsLoading ? 'animate-spin' : ''" />
              <span v-if="recipientsError" class="text-danger">{{ recipientsError }}</span>
              <span v-else-if="pickEmpty" class="text-muted">Pick at least one student.</span>
              <span v-else-if="statusNone" class="text-muted">Tick at least one project status.</span>
              <span v-else-if="recipients" :class="recipientsFresh ? '' : 'opacity-50'">
                <b class="text-charcoal">{{ recipients.unique_students }}</b><span class="text-muted"> student{{ recipients.unique_students === 1 ? '' : 's' }} · </span>
                <b class="text-charcoal">{{ recipients.sendable_count }}</b><span class="text-muted"> e-mail{{ recipients.sendable_count === 1 ? '' : 's' }} (one per project)</span>
                <template v-if="recipients.skipped_count"><span class="text-muted"> · </span><span class="text-warning">{{ recipients.skipped_count }} skipped</span></template>
              </span>
            </span>
            <button
              v-if="recipients && !statusNone && (recipients.sendable_count || recipients.skipped_count)"
              type="button"
              class="font-medium text-primary hover:underline"
              @click="showList = !showList"
            >
              {{ showList ? 'Hide list' : 'View list' }}
            </button>
          </div>
          <RecipientList v-if="showList && recipients && !statusNone" class="mt-3" :preview="recipients" :server-now="env.server_now" />
        </section>

        <!-- 2. the e-mail -->
        <section>
          <h3 class="mb-2 flex items-center gap-2 text-sm font-semibold text-charcoal">
            <span class="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] text-white">2</span>
            The e-mail
          </h3>
          <div class="space-y-3">
            <!-- Own row above the preview: long template names must not spill into it. -->
            <div class="flex flex-wrap items-end gap-x-4 gap-y-2">
              <div class="sirb-fill-select sirb-truncate-select w-full min-w-0 sm:w-96">
                <FormControl v-model="template" type="select" label="Template" :options="templateOptions" />
              </div>
              <div class="flex gap-x-4 pb-1 text-sm">
                <a v-if="template" :href="`/app/email-template/${encodeURIComponent(template)}`" target="_blank" class="font-medium text-primary hover:underline">Edit template</a>
                <a href="/app/email-template/new" target="_blank" class="font-medium text-primary hover:underline">New template</a>
              </div>
            </div>
            <div class="min-w-0 overflow-hidden rounded-lg border border-line">
              <div class="border-b border-line bg-canvas px-4 py-2">
                <p class="text-xs text-muted">
                  Preview<template v-if="preview?.recipient"> for {{ preview.recipient.student_name }} &lt;{{ preview.recipient.email }}&gt;</template>
                  <template v-else-if="preview"> with sample data</template>
                </p>
                <p class="truncate text-sm font-medium text-charcoal">{{ preview?.subject || ' ' }}</p>
              </div>
              <div v-if="template && unknownVariables.length && !previewError" class="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-charcoal">
                Unknown variable{{ unknownVariables.length === 1 ? '' : 's' }}:
                <code v-for="v in unknownVariables" :key="v" class="mr-1 font-semibold">{{ varToken(v) }}</code> — students would see
                {{ unknownVariables.length === 1 ? 'it' : 'them' }} as-is, so fix the template first.
              </div>
              <div class="relative h-64">
                <div v-if="!template" class="flex h-full items-center justify-center text-sm text-muted">Pick a template to preview it.</div>
                <div v-else-if="previewError" class="flex h-full items-center justify-center px-6 text-center text-sm text-danger">{{ previewError }}</div>
                <!-- sandbox="" : no scripts, forms or navigation from template HTML -->
                <iframe v-else-if="preview" sandbox="" :srcdoc="preview.html" title="E-mail preview" class="h-full w-full bg-white" />
                <div v-if="previewLoading" class="absolute inset-0 flex items-center justify-center bg-paper/60">
                  <FeatherIcon name="loader" class="h-5 w-5 animate-spin text-muted" />
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 3. when -->
        <section>
          <h3 class="mb-2 flex items-center gap-2 text-sm font-semibold text-charcoal">
            <span class="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] text-white">3</span>
            When
          </h3>
          <div v-if="!alert" class="mb-3 grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label="When">
            <button
              v-for="w in WHEN_OPTIONS"
              :key="w.v"
              type="button"
              role="radio"
              :aria-checked="whenMode === w.v"
              :class="optionCls(whenMode === w.v)"
              @click="whenMode = w.v; confirming = false"
            >
              <span :class="iconCls(whenMode === w.v)"><FeatherIcon :name="w.i" class="h-4 w-4" /></span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-semibold text-charcoal">{{ w.l }}</span>
                <span class="block text-xs text-muted">{{ w.d }}</span>
              </span>
              <FeatherIcon v-if="whenMode === w.v" name="check-circle" class="h-4 w-4 shrink-0 text-primary" />
            </button>
          </div>
          <div v-if="whenMode === 'schedule'" class="space-y-3 rounded-lg border border-line p-4">
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="p in PRESETS"
                :key="p.key"
                type="button"
                class="rounded-full border px-3 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                :class="schedule.choice === p.key ? 'border-primary bg-primary text-white' : 'border-line text-charcoal hover:border-primary'"
                :disabled="presetDisabled(p)"
                :title="presetDisabled(p) ? 'Already in the past' : ''"
                @click="applyPreset(p.key)"
              >
                {{ p.label }}
              </button>
              <button
                type="button"
                class="rounded-full border px-3 py-1 text-xs font-medium"
                :class="schedule.choice === 'custom' ? 'border-primary bg-primary text-white' : 'border-line text-charcoal hover:border-primary'"
                @click="schedule.choice = 'custom'"
              >
                Custom
              </button>
            </div>
            <div v-if="schedule.choice === 'custom'" class="grid gap-3 sm:grid-cols-3">
              <div>
                <label for="rm-start" class="mb-1 block text-xs text-muted">{{ schedule.frequency === 'Once' ? 'Send at' : 'First reminder at' }}</label>
                <input id="rm-start" v-model="schedule.start_at" type="datetime-local" :class="inputCls" />
              </div>
              <div>
                <label for="rm-repeat" class="mb-1 block text-xs text-muted">Repeat</label>
                <select id="rm-repeat" :value="schedule.frequency" :class="inputCls + ' py-0'" @change="onRepeatChange(($event.target as HTMLSelectElement).value as AlertFrequency)">
                  <option value="Once">Don't repeat</option>
                  <option value="Daily">Every day</option>
                  <option value="Weekly">Every week</option>
                  <option value="Monthly">Every month</option>
                </select>
              </div>
              <div v-if="schedule.frequency !== 'Once'">
                <label for="rm-until" class="mb-1 block text-xs text-muted">Until</label>
                <input id="rm-until" v-model="schedule.end_date" type="date" :class="inputCls" />
              </div>
            </div>
            <p class="text-sm text-charcoal"><FeatherIcon name="clock" class="-mt-0.5 mr-1 inline h-3.5 w-3.5 text-muted" />{{ scheduleSummary }} <span class="text-xs text-muted">(server time, {{ env.timezone }})</span></p>
            <div class="max-w-md">
              <label for="rm-name" class="mb-1 block text-xs text-muted">Reminder name</label>
              <input id="rm-name" v-model="name" type="text" :class="inputCls" @input="nameTouched = true" />
            </div>
            <p class="text-xs text-muted">Recipients are re-checked each time it sends, so students who have moved past these statuses are left out.</p>
            <p v-if="!env.email_configured" class="text-xs text-warning">No outgoing e-mail account is set up yet: scheduled reminders will fail until one is added in Desk.</p>
            <p v-if="!timeline.is_active" class="text-xs text-warning">This timeline is inactive: scheduled reminders won't go out until you make it active again.</p>
          </div>
          <p v-else class="rounded-lg border border-line px-4 py-3 text-sm text-muted">
            The e-mails go out as soon as you confirm{{ emails !== null ? ` (${emails} e-mail${emails === 1 ? '' : 's'})` : '' }}.
          </p>
        </section>

        <p v-if="error" class="text-sm text-danger">{{ error }}</p>
      </div>
    </template>

    <template #actions>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p
          v-if="(whenMode === 'now' && sendBlocker) || (whenMode === 'schedule' && commonBlocker)"
          role="status"
          class="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-700"
        >
          <FeatherIcon name="alert-triangle" class="h-4 w-4 shrink-0 text-amber-600" />
          {{ whenMode === 'now' ? sendBlocker : commonBlocker }}
        </p>
        <span v-else />
        <div class="flex gap-2">
          <template v-if="whenMode === 'now' && confirming">
            <Button variant="outline" :disabled="busy" @click="confirming = false">Back</Button>
            <Button variant="solid" theme="red" icon-left="send" :loading="busy" @click="doSend">
              Yes, send {{ emails }} e-mail{{ emails === 1 ? '' : 's' }} now
            </Button>
          </template>
          <template v-else>
            <Button variant="outline" :disabled="busy" @click="setOpen(false)">Cancel</Button>
            <Button v-if="whenMode === 'now'" variant="solid" icon-left="send" :disabled="!!sendBlocker" @click="askSend">
              {{ emails ? `Send ${emails} e-mail${emails === 1 ? '' : 's'}` : 'Send now' }}
            </Button>
            <Button v-else variant="solid" icon-left="clock" :loading="busy" :disabled="!!commonBlocker" @click="doSchedule">
              {{ alert ? 'Save changes' : 'Schedule reminder' }}
            </Button>
          </template>
        </div>
      </div>
    </template>
  </Dialog>
</template>
