<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Button, toast } from 'frappe-ui'
import AppShell from '@/components/layout/AppShell.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import ErrorState from '@/components/common/ErrorState.vue'
import ProjectHeader from '@/components/projects/ProjectHeader.vue'
import ProjectOverview from '@/components/projects/ProjectOverview.vue'
import StudentInformation from '@/components/projects/StudentInformation.vue'
import PersonCard from '@/components/projects/PersonCard.vue'
import ProjectActions from '@/components/projects/ProjectActions.vue'
import ApprovalTimeline from '@/components/projects/ApprovalTimeline.vue'
import EthicsQuestionnaire from '@/components/projects/EthicsQuestionnaire.vue'
import { useProject } from '@/composables/useProject'
import { useProjectActions } from '@/composables/useProjectActions'
import type { IrbProjectDoc } from '@/types/project'

const props = defineProps<{ name: string }>()

const { detail, history, loading, error, transitioning, load, transitionTo } = useProject(props.name)

// Local editable copy of the doc so field edits don't mutate the loaded
// snapshot until explicitly saved — mirrors Frappe's dirty-doc model.
const localDoc = ref<IrbProjectDoc | null>(null)
const dirty = ref(false)
const saving = ref(false)

onMounted(async () => {
  await load()
  if (detail.value) localDoc.value = { ...detail.value.doc }
})

const roles = computed(() => detail.value?.roles ?? null)
const hasSecondaryReviewer = computed(() => Boolean(localDoc.value?.secondary_reviewer))
const docRef = computed(() => localDoc.value)

const { actions, canEdit } = useProjectActions(docRef, roles, hasSecondaryReviewer)

function updateField(fieldname: string, value: unknown) {
  if (!localDoc.value) return
  localDoc.value = { ...localDoc.value, [fieldname]: value }
  dirty.value = true
}

async function saveChanges() {
  if (!localDoc.value || !detail.value) return
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
    toast.success('Saved successfully')
    dirty.value = false
    await load()
    if (detail.value) localDoc.value = { ...detail.value.doc }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to save')
  } finally {
    saving.value = false
  }
}

async function onAction(status: string) {
  if (dirty.value) {
    await saveChanges()
  }
  await transitionTo(status)
  if (detail.value) localDoc.value = { ...detail.value.doc }
  toast.success('Submitted successfully')
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
        <PersonCard label="Faculty Mentor" :name="localDoc.faculty_mentor" :can-edit-link="false" />
        <PersonCard label="Primary Reviewer" :name="localDoc.primary_reviewer" :can-edit-link="false" />
      </div>

      <div class="mb-4">
        <ProjectOverview :doc="localDoc" :disabled="!canEdit" @update="updateField" />
      </div>

      <div class="mb-4">
        <EthicsQuestionnaire :doc="localDoc" :disabled="!canEdit" @update="updateField" />
      </div>

      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <ProjectActions :actions="actions" :busy="transitioning || saving" @action="onAction" />
        <Button v-if="canEdit && dirty" variant="solid" :loading="saving" @click="saveChanges">Save</Button>
      </div>

      <ApprovalTimeline :history="history" />
    </template>
  </AppShell>
</template>
