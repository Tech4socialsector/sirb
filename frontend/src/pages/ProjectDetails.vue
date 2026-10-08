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
import { useRoles } from '@/composables/useRoles'
import { useTimelineDrawer } from '@/composables/useTimelineDrawer'
import { ApiError } from '@/services/api'
import { fetchProposalIssues } from '@/services/projects'
import type { IrbProjectDoc, ProposalIssue } from '@/types/project'

const props = defineProps<{ name: string }>()

const { detail, history, highlights, loading, error, transitioning, load, transitionTo } = useProject(props.name)
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

// Clearer than the generic API messages for the two cases people hit by
// following an old link or typing an ID into "Go to project".
const projectError = computed(() => {
  if (!error.value) return null
  if (error.value.kind === 'permission')
    return new ApiError(
      "You don't have access to this project. You can open projects you're a student on, mentoring or reviewing.",
      'permission',
    )
  if (error.value.kind === 'not_found')
    return new ApiError(`There's no project with ID “${props.name}”. Check the number and try again.`, 'not_found')
  return null
})

const roles = computed(() => detail.value?.roles ?? null)
// The mentor isn't sent the reviewer fields, so fall back to the server's flag.
const hasSecondaryReviewer = computed(() =>
  Boolean(localDoc.value?.secondary_reviewer || detail.value?.meta.has_secondary_reviewer),
)
// Students and the mentor must not see who is reviewing the project; the
// server also strips the reviewer fields from their payload (sirb_api.project).
const showReviewer = computed(() => Boolean(localDoc.value && 'primary_reviewer' in localDoc.value && !roles.value?.is_student))
// Likewise reviewers aren't shown (or sent) who the mentor is.
const showMentor = computed(() => Boolean(localDoc.value && 'faculty_mentor' in localDoc.value))
const peopleColumns = computed(() => 1 + Number(showMentor.value) + Number(showReviewer.value))
const docRef = computed(() => localDoc.value)

const allowedStatuses = computed(() => detail.value?.allowed_statuses)

// What others changed since this user last had the project — for a student,
// the mentor's / reviewer's feedback (sirb_api.project.get_review_highlights).
const changedFields = computed<ReadonlySet<string>>(() => new Set(Object.keys(highlights.value)))
const FEEDBACK_FIELDS = ['reviewers_comments_to_student', 'mentor_comment_to_student']
const newFeedbackCount = computed(
  () => [...changedFields.value].filter((f) => /_(rf|mf)$/.test(f) || FEEDBACK_FIELDS.includes(f)).length,
)
// Permlevels whose edits this user's saves keep (absent: older server, no limit).
const writableLevels = computed<ReadonlySet<number> | undefined>(() => {
  const levels = detail.value?.meta.writable_permlevels
  return levels ? new Set(levels) : undefined
})
// The proposal's own answers (title, abstract, ... in irb_project.json).
const PROPOSAL_PERMLEVEL = 7
const overviewDisabled = computed(() => !canEdit.value || (writableLevels.value ? !writableLevels.value.has(PROPOSAL_PERMLEVEL) : false))
const { actions, canEdit } = useProjectActions(docRef, roles, hasSecondaryReviewer, allowedStatuses)

// Admins/System Managers — and programme managers on their programmes'
// projects (meta.can_override) — can reassign the mentor and reviewers and
// set the status directly — the server lets them bypass the status workflow
// (sirb.workflow) and still validates the combination (irb_project.py).
const { isAdmin } = useRoles()
const canOverride = computed(() => isAdmin.value || Boolean(detail.value?.meta.can_override))
const ADMIN_EDITABLE_FIELDS: ReadonlySet<string> = new Set(['status', 'faculty_mentor', 'primary_reviewer', 'secondary_reviewer'])
const overrideEditable = computed<ReadonlySet<string>>(() => (canOverride.value ? ADMIN_EDITABLE_FIELDS : new Set()))
const canSave = computed(() => canEdit.value || canOverride.value)

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
    <ErrorState v-else-if="error" :error="projectError ?? error" @retry="load" />
    <template v-else-if="detail && localDoc && roles">
      <ProjectHeader :doc="localDoc" :roles="roles" />

      <div
        v-if="roles.is_student && correctionNoticeStatuses.includes(String(localDoc.status))"
        class="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
      >
        <p v-if="newFeedbackCount" class="mb-1 font-semibold">
          You have new feedback on {{ newFeedbackCount }} {{ newFeedbackCount === 1 ? 'item' : 'items' }}. It's shown
          under each question marked “New review notes” in the questionnaire tabs (look for “updated” on the tab names), and
          overall comments are in the “General comments” tab.
        </p>
        Saving this form only stores your changes. To send your updated documents/answers back to the reviewer, use
        "Submit corrections" below once you're done.
      </div>

      <div
        class="mb-4 grid grid-cols-1 gap-4"
        :class="{ 'md:grid-cols-2': peopleColumns === 2, 'md:grid-cols-3': peopleColumns === 3 }"
      >
        <StudentInformation :students="detail.students" />
        <PersonCard
          v-if="showMentor"
          label="Faculty Mentor"
          :name="localDoc.faculty_mentor"
          :display-name="detail.link_titles?.faculty_mentor"
          :can-edit-link="false"
        />
        <PersonCard
          v-if="showReviewer"
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
        <ProjectOverview :doc="localDoc" :disabled="overviewDisabled" :issue-messages="issueMessages" @update="updateField" />
      </div>

      <div class="mb-4">
        <EthicsQuestionnaire
          ref="questionnaire"
          :doc="localDoc"
          :issue-messages="issueMessages"
          :link-titles="detail.link_titles"
          :disabled="!canEdit"
          :override-editable="overrideEditable"
          :changed-fields="changedFields"
          :writable-levels="writableLevels"
          @update="updateField"
        />
      </div>

      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <ProjectActions :actions="actions" :busy="transitioning || saving || checking" @action="onAction" />
        <div class="flex flex-wrap items-center gap-2">
          <Button v-if="isStudentDraft && canEdit" variant="outline" icon-left="check-circle" :loading="checking" @click="onCheckClick">
            Check for missing answers
          </Button>
          <Button v-if="canSave && dirty" variant="solid" :loading="saving" @click="saveChanges()">Save</Button>
        </div>
      </div>
    </template>
  </AppShell>
</template>
