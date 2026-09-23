<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Checkbox, Dialog, ErrorMessage, FormControl } from 'frappe-ui'
import { saveOrgUnit } from '@/services/setup'
import type { OrgTreeIndex } from '@/utils/orgTree'
import type { AoType, OrgUnit } from '@/types/setup'

const ROOT = '__root__'

const props = defineProps<{
  modelValue: boolean
  /** Unit being edited; omit to create. */
  unit?: OrgUnit | null
  /** Parent fixed by "Add Child" — hides the parent picker, like Desk's tree view. */
  parent?: string | null
  index: OrgTreeIndex
  aoTypes: AoType[]
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [string] }>()

// Same fields, labels and defaults as Desk's tree-view "Add Child" dialog:
// Is Group unchecked, type blank until chosen.
const form = ref({ is_group: false, ao_name: '', ao_type: '' as AoType | '', ao_code: '', parent: ROOT })
const saving = ref(false)
const error = ref('')

const isEdit = computed(() => !!props.unit)
/** Opened via a row's "Add Child": the parent is implied, not picked. */
const fixedParent = computed(() => (!isEdit.value && props.parent && props.index.byName.has(props.parent) ? props.parent : null))
const hasChildren = computed(() => !!props.unit && (props.index.children.get(props.unit.name)?.length ?? 0) > 0)

const typeOptions = computed(() => [
  { label: 'Select type…', value: '', disabled: true },
  ...props.aoTypes.map((t) => ({ label: t, value: t })),
])

const parentOptions = computed(() => [
  { label: 'None — top-level unit', value: ROOT },
  ...props.index.ordered.filter((u) => u.is_group).map((u) => ({ label: props.index.path(u.name), value: u.name })),
])

const previewId = computed(() => {
  const code = form.value.ao_code.trim()
  if (!code) return ''
  return form.value.parent === ROOT ? code : `${form.value.parent}-${code}`
})

// Re-seed every time the dialog opens so a cancelled edit never leaks
// into the next "Add Child" (or vice versa).
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    error.value = ''
    if (props.unit) {
      form.value = {
        is_group: !!props.unit.is_group,
        ao_name: props.unit.ao_name,
        ao_type: props.unit.ao_type,
        ao_code: props.unit.ao_code,
        parent: props.unit.parent || ROOT,
      }
      return
    }
    // Toolbar "Add Unit": default the parent to the first group so a
    // second root isn't created by accident (the server also guards this).
    const parent = fixedParent.value ?? (props.index.ordered.find((u) => u.is_group)?.name || ROOT)
    form.value = { is_group: false, ao_name: '', ao_type: '', ao_code: '', parent }
  },
)

function validate(): string {
  if (!form.value.ao_name.trim()) return 'Enter the Academic Organization Name.'
  if (!form.value.ao_type) return 'Select the Academic Organization Type.'
  if (!isEdit.value) {
    const code = form.value.ao_code.trim()
    if (!code) return 'Enter the Academic Organization Code.'
    if (/[/%#?]/.test(code)) return 'Academic Organization Code cannot contain / % # or ?.'
    if (form.value.parent !== ROOT && !props.index.byName.get(form.value.parent)?.is_group)
      return "The parent must be marked as 'Group'."
    if (props.index.byName.has(previewId.value)) return `A unit with ID "${previewId.value}" already exists.`
  }
  const nameTaken = [...props.index.byName.values()].some(
    (u) => u.name !== props.unit?.name && u.ao_name.trim().toLowerCase() === form.value.ao_name.trim().toLowerCase(),
  )
  if (nameTaken) return 'Another unit already has this name.'
  if (hasChildren.value && !form.value.is_group) return 'This unit has child units, so it must stay a group.'
  return ''
}

async function submit() {
  if (saving.value) return
  error.value = validate()
  if (error.value) return
  saving.value = true
  try {
    const ao_type = form.value.ao_type as AoType
    const name = await saveOrgUnit(
      isEdit.value
        ? { name: props.unit!.name, ao_name: form.value.ao_name.trim(), ao_type, is_group: form.value.is_group }
        : {
            ao_name: form.value.ao_name.trim(),
            ao_code: form.value.ao_code.trim(),
            ao_type,
            is_group: form.value.is_group,
            parent: form.value.parent === ROOT ? undefined : form.value.parent,
            allow_root: form.value.parent === ROOT,
          },
    )
    emit('saved', name)
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not save the unit.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :model-value="modelValue"
    :options="{ title: isEdit ? 'Edit Academic Organizational Unit' : 'New Academic Organizational Unit', size: 'xl' }"
    @update:model-value="(v: boolean) => !saving && emit('update:modelValue', v)"
  >
    <template #body-content>
      <form class="sirb-fill-select space-y-4" @submit.prevent="submit">
        <div v-if="fixedParent" class="rounded-md border border-line bg-canvas px-3 py-2 text-sm">
          <span class="text-muted">Parent:</span>&nbsp;<span class="font-medium text-charcoal">{{ index.path(fixedParent) }}</span>
        </div>

        <div>
          <Checkbox v-model="form.is_group" label="Is Group" :disabled="hasChildren && form.is_group" />
          <p class="mt-1 text-xs text-muted">
            {{
              hasChildren
                ? 'Required: this unit already has child units.'
                : "Further sub-groups can only be created under records marked as 'Group'"
            }}
          </p>
        </div>

        <FormControl v-model="form.ao_name" type="text" label="Academic Organization Name" required />

        <FormControl v-model="form.ao_type" type="select" label="Academic Organization Type" :options="typeOptions" required />

        <div>
          <FormControl v-model="form.ao_code" type="text" label="Academic Organization Code" :disabled="isEdit" required />
          <p v-if="isEdit" class="mt-1.5 text-xs text-muted">
            The code is part of this unit's ID (<span class="font-mono">{{ unit!.name }}</span>), which other records link
            to, so it can't be changed.
          </p>
          <p v-else-if="previewId" class="mt-1.5 text-xs text-muted">
            Unit ID will be <span class="font-mono text-charcoal">{{ previewId }}</span>
          </p>
        </div>

        <!-- Only for the toolbar "Add Unit"; "Add Child" fixes the parent like Desk does. -->
        <FormControl
          v-if="!isEdit && !fixedParent"
          v-model="form.parent"
          type="select"
          label="Parent Academic Organizational Unit"
          :options="parentOptions"
        />

        <ErrorMessage :message="error" />
        <button type="submit" class="hidden" />
      </form>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="saving" @click="emit('update:modelValue', false)">Cancel</Button>
        <Button variant="solid" :loading="saving" @click="submit">{{ isEdit ? 'Save' : 'Create New' }}</Button>
      </div>
    </template>
  </Dialog>
</template>
