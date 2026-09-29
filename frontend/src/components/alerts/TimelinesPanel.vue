<script setup lang="ts">
import { computed } from 'vue'
import { Button, FeatherIcon, Switch } from 'frappe-ui'
import RunStatusBadge from './RunStatusBadge.vue'
import type { IrbTimeline, TimelineAlert, TimelineMilestone } from '@/types/alerts'
import { daysBetween, formatServerDateTime, relativeDays } from '@/utils/serverTime'

const props = defineProps<{
  timelines: IrbTimeline[]
  /** Scheduled reminders; each shows under the activity it is linked to. */
  alerts: TimelineAlert[]
  serverNow: string
  togglingAlert: string | null
  emailConfigured: boolean
}>()
const emit = defineEmits<{
  add: []
  edit: [IrbTimeline]
  delete: [IrbTimeline]
  remind: [IrbTimeline, TimelineMilestone]
  'edit-reminder': [IrbTimeline, TimelineMilestone, TimelineAlert]
  'run-reminder': [TimelineAlert]
  'toggle-reminder': [TimelineAlert, boolean]
  'delete-reminder': [TimelineAlert]
  'open-run': [string]
}>()

const byMilestone = computed(() => {
  const m = new Map<string, TimelineAlert[]>()
  for (const a of props.alerts) if (a.milestone) m.set(a.milestone, [...(m.get(a.milestone) ?? []), a])
  return m
})
const remindersFor = (m: TimelineMilestone) => (m.name ? byMilestone.value.get(m.name) ?? [] : [])

const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
function scheduleText(a: TimelineAlert) {
  const at = (a.start_at || '').slice(11, 16)
  if (a.frequency === 'Once') return `Once · ${formatServerDateTime(a.start_at)}`
  const until = a.end_date ? ` until ${fmt(a.end_date)}` : ''
  if (a.frequency === 'Weekly') {
    const [y, mo, d] = a.start_at.slice(0, 10).split('-').map(Number)
    return `Every ${WEEKDAYS[new Date(Date.UTC(y, mo - 1, d)).getUTCDay()]} at ${at}${until}`
  }
  if (a.frequency === 'Monthly') return `Monthly on day ${Number(a.start_at.slice(8, 10))} at ${at}${until}`
  return `Daily at ${at} from ${fmt(a.start_at)}${until}`
}
function whoText(a: TimelineAlert) {
  const f = a.filters
  const students = f.mode === 'students' ? `${f.student?.length ?? 0} selected student${f.student?.length === 1 ? '' : 's'}` : ''
  const statuses = f.status?.length ? `${f.status.length} status${f.status.length === 1 ? '' : 'es'}` : 'all statuses'
  return students ? `${students} · ${statuses}` : statuses
}
function nextText(a: TimelineAlert) {
  if (!a.enabled) return 'Paused'
  if (a.timeline_inactive) return 'Paused — timeline inactive'
  return a.next_run_at ? `Next ${formatServerDateTime(a.next_run_at)}` : 'Finished'
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
function parts(d: string) {
  const [y, m, day] = d.slice(0, 10).split('-').map(Number)
  return { y, m, day }
}
function fmt(d: string, withYear = true) {
  const p = parts(d)
  return `${p.day} ${MONTHS[p.m - 1]}${withYear ? ` ${p.y}` : ''}`
}
/** "25 Jul 2026", or "25 Jul – 5 Aug 2026" for a range. */
function dateText(m: TimelineMilestone) {
  if (!m.end_date || m.end_date === m.start_date) return fmt(m.start_date)
  const sameYear = parts(m.start_date).y === parts(m.end_date).y
  return `${fmt(m.start_date, !sameYear)} – ${fmt(m.end_date)}`
}

type When = { label: string; cls: string; past: boolean }
function when(m: TimelineMilestone): When {
  const toStart = daysBetween(props.serverNow, m.start_date) ?? 0
  const toEnd = daysBetween(props.serverNow, m.end_date || m.start_date) ?? 0
  if (toEnd < 0) return { label: 'Done', cls: 'bg-canvas text-muted', past: true }
  if (toStart <= 0 && toEnd > 0) return { label: `In progress · ends ${relativeDays(-toEnd)}`, cls: 'bg-blue-50 text-info', past: false }
  if (toEnd === 0) return { label: 'Today', cls: 'bg-amber-50 text-warning', past: false }
  return { label: relativeDays(-toStart), cls: toStart <= 7 ? 'bg-amber-50 text-warning' : 'bg-canvas text-charcoal', past: false }
}

/** A date earlier than the row above is almost always a typo (e.g. the wrong year). */
function outOfOrder(t: IrbTimeline, i: number) {
  return i > 0 && t.milestones[i].start_date < t.milestones[i - 1].start_date
}

/** Index of the next activity that isn't over yet. */
function nextIndex(t: IrbTimeline) {
  return t.milestones.findIndex((m) => !when(m).past)
}

const sorted = computed(() => props.timelines)
</script>

<template>
  <div>
    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <p class="min-w-0 flex-1 text-sm text-muted">
        Each school's IRB calendar for a cycle. Use <b class="font-medium text-charcoal">Remind</b> on an activity to e-mail the students it concerns — right now, or scheduled before the date.
      </p>
      <Button variant="solid" icon-left="plus" class="shrink-0 self-start" @click="emit('add')">New timeline</Button>
    </div>

    <div v-if="!sorted.length" class="rounded-lg border border-dashed border-line px-6 py-12 text-center">
      <FeatherIcon name="calendar" class="mx-auto mb-2 h-6 w-6 text-muted" />
      <p class="text-sm font-medium text-charcoal">No timelines yet</p>
      <p class="mt-1 text-sm text-muted">Add the deadlines your school published for this cycle, e.g. the last date for submitting IRB forms.</p>
    </div>

    <div class="space-y-6">
      <section v-for="t in sorted" :key="t.name" class="overflow-hidden rounded-xl border border-line" :class="t.is_active ? '' : 'opacity-70'">
        <header class="flex flex-wrap items-start justify-between gap-3 border-b border-line bg-canvas px-4 py-3.5 sm:px-5">
          <div class="min-w-0">
            <h3 class="flex flex-wrap items-center gap-2 text-base font-semibold text-charcoal">
              {{ t.timeline_name }}
              <span class="rounded-full px-2 py-0.5 text-[11px] font-medium" :class="t.is_active ? 'bg-green-50 text-success' : 'bg-paper text-muted'">
                {{ t.is_active ? 'Active' : 'Inactive' }}
              </span>
            </h3>
            <p class="mt-0.5 text-xs text-muted">
              Applies to <span class="text-charcoal">{{ t.unit_name || 'all units' }}</span>
              · Cycle <span class="text-charcoal">{{ t.irb_cycle || 'any' }}</span>
              <template v-if="nextIndex(t) >= 0">
                · Next: <span class="text-charcoal">{{ t.milestones[nextIndex(t)].activity }}</span> ({{ when(t.milestones[nextIndex(t)]).label }})
              </template>
            </p>
            <p v-if="t.notes" class="mt-1 text-xs text-muted">{{ t.notes }}</p>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <Button variant="ghost" icon-left="edit-2" @click="emit('edit', t)">Edit</Button>
            <button class="rounded-md p-1.5 text-muted hover:bg-paper hover:text-danger" :aria-label="`Delete ${t.timeline_name}`" title="Delete" @click="emit('delete', t)">
              <FeatherIcon name="trash-2" class="h-4 w-4" />
            </button>
          </div>
        </header>

        <!-- Below md each activity row becomes a stacked card (grid), so nothing scrolls sideways. -->
        <div class="md:overflow-x-auto">
          <table class="w-full text-left text-sm max-md:block md:min-w-[46rem]">
            <thead class="hidden border-b border-line text-xs md:table-header-group font-medium uppercase tracking-wide text-muted">
              <tr>
                <th class="w-10 px-4 py-2">#</th>
                <th class="px-3 py-2">Activity</th>
                <th class="w-52 px-3 py-2">Date</th>
                <th class="w-44 px-3 py-2">Time / note</th>
                <th class="w-40 px-3 py-2">When</th>
                <th class="w-36 px-3 py-2 text-right">Reminders</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-line max-md:block">
              <template v-for="(m, i) in t.milestones" :key="m.name || i">
              <tr
                class="max-md:grid max-md:grid-cols-[1.25rem_minmax(0,1fr)_auto] max-md:items-center max-md:gap-x-2 max-md:gap-y-2 max-md:px-4 max-md:py-3"
                :class="[i === nextIndex(t) && t.is_active ? 'bg-blue-50/40' : '', when(m).past ? 'text-muted' : 'text-charcoal']"
              >
                <td class="px-4 py-2.5 align-top text-xs text-muted max-md:self-start max-md:p-0 max-md:pt-0.5">{{ i + 1 }}</td>
                <td class="px-3 py-2.5 align-top max-md:col-span-2 max-md:p-0">
                  <p class="font-medium" :class="when(m).past ? 'text-muted' : 'text-charcoal'">{{ m.activity }}</p>
                  <p v-if="m.remind_statuses.length" class="mt-0.5 text-xs text-muted" :title="m.remind_statuses.join('\n')">
                    Remind: {{ m.remind_statuses.length === 1 ? m.remind_statuses[0] : `${m.remind_statuses.length} statuses` }}
                  </p>
                </td>
                <td class="whitespace-nowrap px-3 py-2.5 align-top max-md:col-start-2 max-md:row-start-2 max-md:whitespace-normal max-md:p-0">
                  <span class="inline-flex items-center gap-1.5">
                    {{ dateText(m) }}
                    <FeatherIcon
                      v-if="outOfOrder(t, i)"
                      name="alert-triangle"
                      class="h-3.5 w-3.5 text-warning"
                      :title="`This date is before the previous activity (${fmt(t.milestones[i - 1].start_date)}). Check the year?`"
                    />
                  </span>
                </td>
                <td class="px-3 py-2.5 align-top text-xs max-md:col-start-2 max-md:row-start-3 max-md:p-0" :class="m.time_note ? '' : 'max-md:hidden'">{{ m.time_note || '' }}</td>
                <td class="px-3 py-2.5 align-top max-md:col-start-3 max-md:row-start-2 max-md:justify-self-end max-md:p-0">
                  <span class="whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium" :class="when(m).cls">{{ when(m).label }}</span>
                </td>
                <td class="px-3 py-2.5 text-right align-top max-md:col-start-3 max-md:row-start-3 max-md:justify-self-end max-md:p-0">
                  <Button size="sm" variant="outline" icon-left="bell" :disabled="!m.name" @click="emit('remind', t, m)">Remind</Button>
                </td>
              </tr>
              <!-- this activity's scheduled reminders -->
              <tr v-if="remindersFor(m).length" :key="`${m.name}-reminders`" class="!border-t-0 max-md:block max-md:px-4 max-md:pb-3">
                <td class="max-md:hidden" />
                <td colspan="5" class="px-3 pb-3 pt-0 max-md:block max-md:p-0">
                  <ul class="space-y-1.5">
                    <li
                      v-for="a in remindersFor(m)"
                      :key="a.name"
                      class="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md border border-line bg-canvas px-3 py-2 text-xs"
                      :class="a.enabled ? '' : 'opacity-70'"
                    >
                      <Switch
                        :model-value="!!a.enabled"
                        :disabled="togglingAlert === a.name"
                        :aria-label="a.enabled ? `Pause ${a.alert_name}` : `Resume ${a.alert_name}`"
                        @update:model-value="(v: boolean) => emit('toggle-reminder', a, v)"
                      />
                      <span class="min-w-0">
                        <span class="block truncate text-sm font-medium text-charcoal">{{ a.alert_name }}</span>
                        <span class="block text-muted">{{ scheduleText(a) }} · {{ whoText(a) }}</span>
                      </span>
                      <span class="whitespace-nowrap" :class="a.timeline_inactive ? 'text-warning' : a.enabled && a.next_run_at ? 'text-charcoal' : 'text-muted'">{{ nextText(a) }}</span>
                      <button v-if="a.last_run && a.last_run_status" type="button" :title="'Last sent ' + formatServerDateTime(a.last_run_at)" @click="emit('open-run', a.last_run!)">
                        <RunStatusBadge :status="a.last_run_status" />
                      </button>
                      <span class="ml-auto flex items-center gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          icon-left="send"
                          :disabled="a.is_running || !emailConfigured"
                          :title="a.is_running ? 'Already sending' : !emailConfigured ? 'No outgoing e-mail account' : 'Send it now (the schedule stays)'"
                          @click="emit('run-reminder', a)"
                          >Send now</Button
                        >
                        <Button size="sm" variant="ghost" icon-left="edit-2" @click="emit('edit-reminder', t, m, a)">Edit</Button>
                        <button
                          type="button"
                          class="rounded p-1 text-muted hover:bg-paper hover:text-danger disabled:opacity-40"
                          :disabled="a.is_running"
                          :aria-label="`Delete reminder ${a.alert_name}`"
                          title="Delete reminder"
                          @click="emit('delete-reminder', a)"
                        >
                          <FeatherIcon name="trash-2" class="h-3.5 w-3.5" />
                        </button>
                      </span>
                    </li>
                  </ul>
                </td>
              </tr>
              </template>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>
