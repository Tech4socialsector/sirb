<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Button, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectHeader from '@/components/projects/ProjectHeader.vue'
import ProjectOverview from '@/components/projects/ProjectOverview.vue'
import StudentInformation from '@/components/projects/StudentInformation.vue'
import PersonCard from '@/components/projects/PersonCard.vue'
import ProjectActions from '@/components/projects/ProjectActions.vue'
import EthicsQuestionnaire from '@/components/projects/EthicsQuestionnaire.vue'
import ProposalIssues from '@/components/projects/ProposalIssues.vue'
import { useProject } from '@/composables/useProject'
import { useProjectActions } from '@/composables/useProjectActions'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import { fetchProposalIssues } from '@/services/projects'
import type { IrbProjectDoc, ProposalIssue } from '@/types/project'

const props = defineProps<{ name: string }>()

const { detail, history, loading, error, transitioning, load, transitionTo } = useProject(props.name)
const { setContext, clearContext } = useTimelineDrawer()

// Local editable copy of the doc so field edits don't mutate the loaded
// snapshot until explicitly saved — mirrors Frappe's dirty-doc model.
const localDoc = ref<IrbProjectDoc | null>(null)
const dirty = ref(false)
const saving = ref(false)

onMounted(async () => {
  await load()
  if (detail.value) localDoc.value = { ...detail.value.doc }
})

// Keep the global header's Timeline drawer in sync with this page's
// already-loaded data — the drawer never fetches on its own, so it stays
// current across saves/transitions for free.
watch(
  [detail, history, loading],
  ([d, h, isLoading]) => {
    setContext({
      projectName: props.name,
      projectTitle: d?.doc.title ?? null,
      studentName: d?.students.map((s) => s.full_name).join(', ') || null,
      currentStatus: d?.doc.status ?? null,
      history: h,
      loading: isLoading && !d,
    })
  },
  { immediate: true },
)

onUnmounted(() => clearContext())

const roles = computed(() => detail.value?.roles ?? null)
const hasSecondaryReviewer = computed(() => Boolean(localDoc.value?.secondary_reviewer))
const docRef = computed(() => localDoc.value)

const { actions, canEdit } = useProjectActions(docRef, roles, hasSecondaryReviewer)

// Statuses in which the student is writing/correcting the proposal —
// must match STUDENT_DRAFT_STATUSES in irb_project.py.
const STUDENT_DRAFT_STATUSES = [
  'Awaiting proposal completion by student',
  'Awaiting student correction for mentor feedback',
  'Awaiting student correction for reviewer feedback',
]
const isStudentDraft = computed(
  () => Boolean(roles.value?.is_student) && STUDENT_DRAFT_STATUSES.includes(String(localDoc.value?.status)),
)

// Unanswered questions blocking submission (null = not checked yet).
const issues = ref<ProposalIssue[] | null>(null)
const checking = ref(false)
const issueMessages = computed(() => new Map((issues.value || []).map((i) => [i.fieldname, i.message])))
const issuesPanel = ref<HTMLElement | null>(null)
const questionnaire = ref<InstanceType<typeof EthicsQuestionnaire> | null>(null)

function isAnswered(value: unknown) {
  if (typeof value === 'boolean' || typeof value === 'number') return Boolean(value)
  const text = String(value ?? '').replace(/<[^>]*>/g, '').trim()
  return text !== '' && text !== '-- Select --'
}

function updateField(fieldname: string, value: unknown) {
  if (!localDoc.value) return
  localDoc.value = { ...localDoc.value, [fieldname]: value }
  dirty.value = true
  // Tick the question off the list as soon as it's answered.
  if (issues.value && isAnswered(value)) issues.value = issues.value.filter((i) => i.fieldname !== fieldname)
}

/** Saves unsaved edits. Returns false (after telling the user) on failure,
 * so callers never go on to submit a proposal whose edits didn't save. */
async function saveChanges(opts: { silent?: boolean } = {}): Promise<boolean> {
  if (!localDoc.value || !detail.value) return false
  saving.value = true
  try {
    const { saveProjectFields } = await import('@/services/projects')
    const changed: Record<string, unknown> = {}
    for (const key of Object.keys(localDoc.value)) {
      if (localDoc.value[key] !== detail.value.doc[key]) changed[key] = localDoc.value[key]
    }
    if (Object.keys(changed).length) {
      await saveProjectFields(props.name, changed)
    }
    if (!opts.silent) toast.success('Saved successfully')
    dirty.value = false
    await load()
    if (detail.value) localDoc.value = { ...detail.value.doc }
    return true
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to save')
    return false
  } finally {
    saving.value = false
  }
}

async function showIssues(list: ProposalIssue[]) {
  issues.value = list
  await nextTick()
  issuesPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/** Save, then ask the server (same rules it enforces on submit) what's missing. */
async function checkProposal(): Promise<ProposalIssue[] | null> {
  if (dirty.value && !(await saveChanges({ silent: true }))) return null
  checking.value = true
  try {
    return await fetchProposalIssues(props.name)
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Could not check your proposal. Please try again.')
    return null
  } finally {
    checking.value = false
  }
}

async function onCheckClick() {
  const list = await checkProposal()
  if (!list) return
  if (list.length) await showIssues(list)
  else {
    issues.value = []
    toast.success('Everything is answered — your proposal is ready to submit.')
  }
}

async function jumpTo(issue: ProposalIssue) {
  const found = await questionnaire.value?.focusField(issue.fieldname)
  if (found) return
  // Basic details live outside the questionnaire tabs.
  const el = document.getElementById(`field-${issue.fieldname}`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el?.querySelector<HTMLElement>('textarea, input, [data-slot="trigger"]')?.focus({ preventScroll: true })
}

async function onAction(status: string) {
  if (transitioning.value || saving.value || checking.value) return
  if (isStudentDraft.value) {
    // Submitting: make sure nothing is missing first, and show all of it.
    const list = await checkProposal()
    if (!list) return
    if (list.length) {
      await showIssues(list)
      toast.error(`${list.length} ${list.length === 1 ? 'question needs' : 'questions need'} an answer before you can submit.`)
      return
    }
  } else if (dirty.value && !(await saveChanges({ silent: true }))) {
    return
  }
  try {
    await transitionTo(status)
    if (detail.value) localDoc.value = { ...detail.value.doc }
    issues.value = null
    toast.success('Submitted successfully')
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Could not submit. Please try again.')
    // If the server found gaps the check missed (e.g. a co-member edited
    // the proposal meanwhile), show the fresh list.
    if (isStudentDraft.value) {
      const list = await fetchProposalIssues(props.name).catch(() => null)
      if (list?.length) await showIssues(list)
    }
  }
}

const correctionNoticeStatuses = [
  'Awaiting student correction for mentor feedback',
  'Awaiting student correction for reviewer feedback',
]
</script>

<template>
  <AppShell>
    <LoadingState v-if="loading && !detail" label="Loading project…" />
    <ErrorState v-else-if="error" :error="error" @retry="load" />
    <template v-else-if="detail && localDoc && roles">
      <ProjectHeader :doc="localDoc" :roles="roles" />

      <div
        v-if="roles.is_student && correctionNoticeStatuses.includes(String(localDoc.status))"
        class="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
      >
        Saving this form only stores your changes. To send your updated documents/answers back to the reviewer, use
        "Submit corrections" below once you're done.
      </div>

      <div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <StudentInformation :students="detail.students" />
        <PersonCard
          label="Faculty Mentor"
          :name="localDoc.faculty_mentor"
          :display-name="detail.link_titles?.faculty_mentor"
          :can-edit-link="false"
        />
        <PersonCard
          label="Primary Reviewer"
          :name="localDoc.primary_reviewer"
          :display-name="detail.link_titles?.primary_reviewer"
          :can-edit-link="false"
        />
      </div>

      <div v-if="issues && issues.length" ref="issuesPanel" class="mb-4 scroll-mt-24">
        <ProposalIssues :issues="issues" @jump="jumpTo" @close="issues = null" />
      </div>

      <div class="mb-4">
        <ProjectOverview :doc="localDoc" :disabled="!canEdit" :issue-messages="issueMessages" @update="updateField" />
      </div>

      <div class="mb-4">
        <EthicsQuestionnaire
          ref="questionnaire"
          :doc="localDoc"
          :issue-messages="issueMessages"
          :link-titles="detail.link_titles"
          :disabled="!canEdit"
          @update="updateField"
        />
      </div>

      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <ProjectActions :actions="actions" :busy="transitioning || saving || checking" @action="onAction" />
        <div class="flex flex-wrap items-center gap-2">
          <Button v-if="isStudentDraft && canEdit" variant="outline" icon-left="check-circle" :loading="checking" @click="onCheckClick">
            Check for missing answers
          </Button>
          <Button v-if="canEdit && dirty" variant="solid" :loading="saving" @click="saveChanges()">Save</Button>
        </div>
      </div>
    </template>
  </AppShell>
</template>
