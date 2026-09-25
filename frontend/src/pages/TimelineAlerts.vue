<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Button, FeatherIcon, Switch, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import DataTable, { type DataTableColumn } from '@/components/common/DataTable.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import TimelinesPanel from '@/components/alerts/TimelinesPanel.vue'
import TimelineDialog from '@/components/alerts/TimelineDialog.vue'
import ReminderDialog from '@/components/alerts/ReminderDialog.vue'
import RunDetailsDialog from '@/components/alerts/RunDetailsDialog.vue'
import RunStatusBadge from '@/components/alerts/RunStatusBadge.vue'
import {
  deleteAlert,
  deleteTimeline,
  fetchAlertPageData,
  fetchAlerts,
  fetchRuns,
  fetchTemplates,
  fetchTimelines,
  runAlertNow,
  setAlertEnabled,
} from '@/services/alerts'
import { ApiError } from '@/services/api'
import type { AlertPageData, AlertRun, IrbTimeline, TimelineAlert, TimelineMilestone } from '@/types/alerts'
import { describeFilters } from '@/utils/alertFilters'
import { formatServerDateTime, serverClock } from '@/utils/serverTime'

/**
 * Timeline Alerts: each school's IRB timeline as a table. Remind on an
 * activity e-mails the students it concerns — now, or scheduled before the
 * deadline — and its scheduled reminders are listed under that activity.
 */

// ---- page data
const data = ref<AlertPageData | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref<ApiError | null>(null)
const runs = ref<AlertRun[]>([])
// Tracks server wall time from the moment the page data arrived.
const clock = ref<ReturnType<typeof serverClock> | null>(null)

async function load() {
  if (data.value) refreshing.value = true
  else loading.value = true
  error.value = null
  try {
    const [page, runList] = await Promise.all([fetchAlertPageData(), fetchRuns()])
    data.value = page
    runs.value = runList
    clock.value = serverClock(page.environment.server_now)
  } catch (e) {
    const err = e instanceof ApiError ? e : new ApiError('Failed to load timeline alerts.', 'server')
    if (data.value) toast.error(err.message)
    else error.value = err
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

/** Reminders, runs and timelines (reminder rows and counts live in all three). */
async function refreshLists() {
  try {
    const [alertList, runList, timelines] = await Promise.all([fetchAlerts(), fetchRuns(), fetchTimelines()])
    if (data.value) {
      data.value.alerts = alertList
      data.value.timelines = timelines
    }
    runs.value = runList
  } catch {
    // A failed background refresh keeps the last good lists on screen.
  }
}

const env = computed(() => data.value?.environment)
const alerts = computed(() => data.value?.alerts ?? [])
/** Reminders not tied to a timeline activity (older alerts, or made in Desk). */
const otherAlerts = computed(() => alerts.value.filter((a) => !a.timeline))
const unitNames = computed(() => new Map((data.value?.units ?? []).map((u) => [u.name, u.ao_name])))

// Templates are edited in Desk (another tab): pick up new / renamed ones on return.
let lastRefresh = 0
async function onPageVisible() {
  if (document.visibilityState !== 'visible' || !data.value || Date.now() - lastRefresh < 1500) return
  lastRefresh = Date.now()
  try {
    const templates = await fetchTemplates()
    if (data.value) data.value.templates = templates
  } catch {
    // keep the current list; the next visit retries
  }
}

// ---- timelines
const timelineDialog = ref({ open: false, timeline: null as IrbTimeline | null })
function onTimelineSaved() {
  toast.success(timelineDialog.value.timeline ? 'Timeline updated.' : 'Timeline created.')
  refreshLists()
}

// ---- reminder dialog (new, or editing a scheduled one)
const reminder = ref({
  open: false,
  timeline: null as IrbTimeline | null,
  milestone: null as TimelineMilestone | null,
  alert: null as TimelineAlert | null,
})
function remind(t: IrbTimeline, m: TimelineMilestone) {
  reminder.value = { open: true, timeline: t, milestone: m, alert: null }
}
function editReminder(t: IrbTimeline, m: TimelineMilestone, a: TimelineAlert) {
  reminder.value = { open: true, timeline: t, milestone: m, alert: a }
}
function onReminderSent() {
  toast.success('Reminder queued. Its progress shows under "Recently sent".')
  refreshLists()
}
function onReminderSaved() {
  toast.success(reminder.value.alert ? 'Reminder updated.' : 'Reminder scheduled.')
  refreshLists()
}

// ---- confirmations (delete timeline / reminder, send a reminder now)
const confirm = ref({ open: false, title: '', message: '', label: 'Confirm', run: async () => {} })
function askConfirm(title: string, message: string, label: string, action: () => Promise<void>) {
  confirm.value = { open: true, title, message, label, run: action }
}
function guarded(action: () => Promise<unknown>, success: string, failure: string) {
  return async () => {
    try {
      await action()
      toast.success(success)
      await refreshLists()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : failure)
      throw e // keeps the confirmation open
    }
  }
}
function confirmDeleteTimeline(t: IrbTimeline) {
  askConfirm(
    `Delete "${t.timeline_name}"?`,
    'Its activities are removed. Delete the reminders scheduled for them first.',
    'Delete',
    guarded(() => deleteTimeline(t.name), `"${t.timeline_name}" deleted.`, 'Could not delete the timeline.'),
  )
}
function confirmRunReminder(a: TimelineAlert) {
  askConfirm(
    `Send "${a.alert_name}" now?`,
    'The students are worked out right now from its settings. Its schedule does not change.',
    'Send now',
    guarded(() => runAlertNow(a.name), 'Reminder queued. Its progress shows under "Recently sent".', 'Could not send the reminder.'),
  )
}
function confirmDeleteReminder(a: TimelineAlert) {
  askConfirm(
    `Delete "${a.alert_name}"?`,
    'It will not send again. What it already sent stays under "Recently sent".',
    'Delete',
    guarded(() => deleteAlert(a.name), `"${a.alert_name}" deleted.`, 'Could not delete the reminder.'),
  )
}

const togglingAlert = ref<string | null>(null)
async function toggleReminder(a: TimelineAlert, enabled: boolean) {
  if (togglingAlert.value) return
  togglingAlert.value = a.name
  try {
    const r = await setAlertEnabled(a.name, enabled)
    a.enabled = r.enabled
    a.next_run_at = r.next_run_at
    toast.success(enabled ? `"${a.alert_name}" resumed.` : `"${a.alert_name}" paused.`)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Could not update the reminder.')
  } finally {
    togglingAlert.value = null
  }
}

// ---- recently sent
const runColumns: DataTableColumn[] = [
  { key: 'creation', label: 'Sent', sortable: true },
  { key: 'alert_name', label: 'Reminder', sortable: true },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'sent_count', label: 'E-mails', align: 'right', sortable: true },
  { key: 'skipped_count', label: 'Skipped', align: 'right', sortable: true },
  { key: 'failed_count', label: 'Failed', align: 'right', sortable: true },
]
const runDialog = ref({ open: false, name: null as string | null })
function openRun(name: string) {
  runDialog.value = { open: true, name }
}

// Poll while something is sending, so statuses and counts update by themselves.
const hasActiveRuns = computed(() => runs.value.some((r) => r.status === 'Queued' || r.status === 'Running'))
let pollTimer: ReturnType<typeof setInterval> | undefined
watch(
  hasActiveRuns,
  (active) => {
    clearInterval(pollTimer)
    pollTimer = active ? setInterval(refreshLists, 4000) : undefined
  },
  { immediate: true },
)

onMounted(() => {
  document.addEventListener('visibilitychange', onPageVisible)
  window.addEventListener('focus', onPageVisible)
  load()
})
onUnmounted(() => {
  document.removeEventListener('visibilitychange', onPageVisible)
  window.removeEventListener('focus', onPageVisible)
  clearInterval(pollTimer)
})

function rowAs<T>(row: unknown) {
  return row as T
}
</script>

<template>
  <AppShell>
    <PageHeader title="Timeline Alerts" description="Each school's IRB timeline. Remind students about an activity now, or schedule reminders before its date.">
      <template #actions>
        <Button variant="outline" icon-left="refresh-cw" :loading="refreshing" :disabled="loading" @click="load">Refresh</Button>
      </template>
    </PageHeader>

    <LoadingState v-if="loading && !data" label="Loading timelines…" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <template v-else-if="data && env && clock">
      <!-- Environment warnings -->
      <div v-if="!env.email_configured || env.email_muted || !env.scheduler_active || !data.templates.length" class="mb-5 space-y-2">
        <div v-if="!env.email_configured" class="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm">
          <FeatherIcon name="alert-octagon" class="mt-0.5 h-4 w-4 shrink-0 text-danger" />
          <p class="text-charcoal">
            No outgoing e-mail account is set up, so reminders can't be sent.
            <a href="/app/email-account/new" target="_blank" class="font-medium text-primary hover:underline">Add one in Desk</a>
            (enable "Outgoing" and "Default Outgoing").
          </p>
        </div>
        <div v-if="env.email_muted" class="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
          <FeatherIcon name="volume-x" class="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p class="text-charcoal">E-mails are muted on this site (<code>mute_emails</code>). Reminders are queued but not delivered.</p>
        </div>
        <div v-if="!env.scheduler_active" class="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
          <FeatherIcon name="pause-circle" class="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <p class="text-charcoal">
            The background scheduler is off, so scheduled reminders won't go out until it's enabled (<code>bench --site &lt;site&gt; enable-scheduler</code>).
          </p>
        </div>
        <div v-if="!data.templates.length" class="flex items-start gap-3 rounded-lg border border-line bg-paper px-4 py-3 text-sm">
          <FeatherIcon name="info" class="mt-0.5 h-4 w-4 shrink-0 text-info" />
          <p class="text-charcoal">
            There are no e-mail templates yet.
            <a href="/app/email-template/new" target="_blank" class="font-medium text-primary hover:underline">Create one in Desk</a>, then click Refresh.
          </p>
        </div>
      </div>

      <div class="rounded-xl border border-line bg-paper p-4 shadow-card sm:p-6">
        <TimelinesPanel
          :timelines="data.timelines"
          :alerts="alerts"
          :server-now="env.server_now"
          :toggling-alert="togglingAlert"
          :email-configured="env.email_configured"
          @add="timelineDialog = { open: true, timeline: null }"
          @edit="(t) => (timelineDialog = { open: true, timeline: t })"
          @delete="confirmDeleteTimeline"
          @remind="remind"
          @edit-reminder="editReminder"
          @run-reminder="confirmRunReminder"
          @toggle-reminder="toggleReminder"
          @delete-reminder="confirmDeleteReminder"
          @open-run="openRun"
        />
      </div>

      <!-- Reminders that aren't linked to a timeline still run: keep them visible. -->
      <div v-if="otherAlerts.length" class="mt-6 rounded-xl border border-line bg-paper p-4 shadow-card sm:p-6">
        <h2 class="text-sm font-semibold text-charcoal">Other scheduled reminders</h2>
        <p class="mb-3 text-xs text-muted">Not linked to a timeline activity. Pause or delete them here.</p>
        <ul class="space-y-1.5">
          <li v-for="a in otherAlerts" :key="a.name" class="flex flex-wrap items-center gap-3 rounded-md border border-line bg-canvas px-3 py-2 text-xs">
            <Switch :model-value="!!a.enabled" :disabled="togglingAlert === a.name" @update:model-value="(v: boolean) => toggleReminder(a, v)" />
            <span class="min-w-0">
              <span class="block truncate text-sm font-medium text-charcoal">{{ a.alert_name }}</span>
              <span class="block text-muted">{{ a.frequency }} · {{ describeFilters(a.filters, data.filter_options, undefined, unitNames).join(' · ') }}</span>
            </span>
            <span class="text-muted">{{ a.enabled ? (a.next_run_at ? `Next ${formatServerDateTime(a.next_run_at)}` : 'Finished') : 'Paused' }}</span>
            <span class="ml-auto flex items-center gap-1">
              <Button size="sm" variant="ghost" icon-left="send" :disabled="a.is_running || !env.email_configured" @click="confirmRunReminder(a)">Send now</Button>
              <button type="button" class="rounded p-1 text-muted hover:bg-paper hover:text-danger" :aria-label="`Delete reminder ${a.alert_name}`" @click="confirmDeleteReminder(a)">
                <FeatherIcon name="trash-2" class="h-3.5 w-3.5" />
              </button>
            </span>
          </li>
        </ul>
      </div>

      <!-- Recently sent -->
      <div class="mt-6 rounded-xl border border-line bg-paper p-4 shadow-card sm:p-6">
        <div class="mb-3">
          <h2 class="flex items-center gap-2 text-sm font-semibold text-charcoal">
            Recently sent
            <span v-if="hasActiveRuns" class="h-2 w-2 animate-pulse rounded-full bg-info" title="A reminder is being sent" />
          </h2>
          <p class="text-xs text-muted">Manual and scheduled reminders. Click one for the per-student results.</p>
        </div>
        <DataTable
          :columns="runColumns"
          :rows="runs as unknown as Record<string, unknown>[]"
          row-key="name"
          clickable-rows
          :page-size="5"
          empty-title="Nothing sent yet"
          empty-description="Reminders you send or schedule from the timelines appear here."
          @row-click="(r) => openRun(rowAs<AlertRun>(r).name)"
        >
          <template #cell-creation="{ value }">{{ formatServerDateTime(value as string) }}</template>
          <template #cell-alert_name="{ row }">
            <p class="font-medium text-charcoal">{{ rowAs<AlertRun>(row).alert_name }}</p>
            <p class="text-xs text-muted">
              {{ rowAs<AlertRun>(row).trigger }}<template v-if="rowAs<AlertRun>(row).deadline_label"> · {{ rowAs<AlertRun>(row).deadline_label }}</template>
            </p>
          </template>
          <template #cell-status="{ value }"><RunStatusBadge :status="value as AlertRun['status']" /></template>
          <template #cell-failed_count="{ value }">
            <span :class="(value as number) ? 'font-semibold text-danger' : ''">{{ value }}</span>
          </template>
        </DataTable>
      </div>

      <ReminderDialog
        v-model="reminder.open"
        :timeline="reminder.timeline"
        :milestone="reminder.milestone"
        :alert="reminder.alert"
        :templates="data.templates"
        :statuses="data.filter_options.statuses"
        :env="env"
        :clock="clock"
        @sent="onReminderSent"
        @saved="onReminderSaved"
      />
      <TimelineDialog
        v-model="timelineDialog.open"
        :timeline="timelineDialog.timeline"
        :units="data.units"
        :cycles="data.filter_options.cycles"
        :statuses="data.filter_options.statuses"
        :server-now="env.server_now"
        @saved="onTimelineSaved"
      />
      <RunDetailsDialog v-model="runDialog.open" :run-name="runDialog.name" :options="data.filter_options" />
      <ConfirmDialog v-model="confirm.open" :title="confirm.title" :message="confirm.message" :confirm-label="confirm.label" :on-confirm="confirm.run" />
    </template>
  </AppShell>
</template>
