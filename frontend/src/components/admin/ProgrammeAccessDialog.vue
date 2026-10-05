<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FormControl, FormLabel, MultiSelect } from 'frappe-ui'
import LinkField from '@/components/common/LinkField.vue'
import {
  saveProgrammeAccess,
  type AccessLevel,
  type ProgrammeAccessRecord,
  type ProgrammeOption,
} from '@/services/programmeAccess'

const props = defineProps<{
  modelValue: boolean
  /** Record being edited; omit to grant access to a new user. */
  record?: ProgrammeAccessRecord | null
  programmes: ProgrammeOption[]
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [string] }>()

const user = ref<string | undefined>()
const selected = ref<string[]>([])
const accessLevel = ref<AccessLevel>('Read only')
const ACCESS_LEVEL_OPTIONS = [
  { label: 'Read only — view the Admin Console', value: 'Read only' },
  { label: 'Read & Write — also reassign mentor/reviewers and set status', value: 'Read & Write' },
]
const saving = ref(false)
const error = ref('')

const isEdit = computed(() => !!props.record)
const programmeOptions = computed(() =>
  props.programmes.map((p) => ({
    label: `${p.ao_name || p.name} (${p.project_count} project${p.project_count === 1 ? '' : 's'})`,
    value: p.name,
  })),
)

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    error.value = ''
    user.value = props.record?.user
    accessLevel.value = props.record?.access_level ?? 'Read only'
    // Drop programmes deleted since this record was saved, so they can't be resubmitted.
    const known = new Set(props.programmes.map((p) => p.name))
    selected.value = (props.record?.programmes ?? []).map((p) => p.irb_unit).filter((p) => known.has(p))
  },
)

async function submit() {
  if (saving.value) return
  error.value = !user.value ? 'Select a user.' : !selected.value.length ? 'Select at least one programme.' : ''
  if (error.value) return
  saving.value = true
  try {
    const name = await saveProgrammeAccess(user.value!, selected.value, !isEdit.value, accessLevel.value)
    emit('saved', name)
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not save programme access.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :model-value="modelValue"
    :options="{ title: isEdit ? `Programme access — ${record?.full_name || record?.user}` : 'Grant Programme Access', size: 'xl' }"
    @update:model-value="(v: boolean) => !saving && emit('update:modelValue', v)"
  >
    <template #body-content>
      <div class="space-y-4">
        <FormControl v-if="isEdit" :model-value="record?.user" type="text" label="User" disabled />
        <LinkField v-else v-model="user" doctype="User" label="User" required />

        <FormControl v-model="accessLevel" type="select" label="Access Level" :options="ACCESS_LEVEL_OPTIONS" required />

        <div class="space-y-1.5">
          <FormLabel label="Programmes" required />
          <MultiSelect
            v-model="selected"
            :options="programmeOptions"
            placeholder="Select programmes"
            empty-text="No IRB Units set up yet"
            class="w-full"
          />
        </div>

        <p v-if="accessLevel === 'Read & Write'" class="text-sm text-muted">
          The user gets the <span class="font-medium text-charcoal">IRB Programme Manager</span> role: the Admin Console
          for these programmes, plus opening their projects to reassign the mentor and reviewers and set the status, like
          an administrator. They can't edit proposal answers or move a project to another programme.
        </p>
        <p v-else class="text-sm text-muted">
          The user gets the <span class="font-medium text-charcoal">IRB Programme Viewer</span> role: a read-only Admin
          Console showing these programmes only. They can't open or edit projects.
        </p>

        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="saving" @click="emit('update:modelValue', false)">Cancel</Button>
        <Button variant="solid" :loading="saving" @click="submit">{{ isEdit ? 'Save' : 'Grant Access' }}</Button>
      </div>
    </template>
  </Dialog>
</template>
