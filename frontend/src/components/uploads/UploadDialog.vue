<script setup lang="ts">
import { ref } from 'vue'
import { Button, Dialog, FormControl } from 'frappe-ui'
import LinkField from '@/components/common/LinkField.vue'

export interface UploadField {
  fieldname: string
  label: string
  type: 'link' | 'text'
  doctype?: string
  required?: boolean
}

const props = defineProps<{
  modelValue: boolean
  title: string
  fields: UploadField[]
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  submit: [{ values: Record<string, string>; file: File }]
}>()

const values = ref<Record<string, string>>({})
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] || null
}

function setValue(fieldname: string, value: string | undefined) {
  values.value = { ...values.value, [fieldname]: value ?? '' }
}

function canSubmit() {
  if (!file.value) return false
  return props.fields.every((f) => !f.required || values.value[f.fieldname])
}

function submit() {
  if (!file.value || !canSubmit()) return
  emit('submit', { values: values.value, file: file.value })
}

function reset() {
  values.value = {}
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
}

defineExpose({ reset })
</script>

<template>
  <Dialog
    :model-value="modelValue"
    :options="{ title }"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <template #body-content>
      <div class="space-y-4">
        <template v-for="field in fields" :key="field.fieldname">
          <LinkField
            v-if="field.type === 'link'"
            :doctype="field.doctype!"
            :label="field.label"
            :required="field.required"
            :model-value="values[field.fieldname]"
            @update:model-value="(v) => setValue(field.fieldname, v)"
          />
          <FormControl
            v-else
            type="text"
            :label="field.label"
            :required="field.required"
            :model-value="values[field.fieldname]"
            @update:model-value="(v: string) => setValue(field.fieldname, v)"
          />
        </template>
        <div>
          <label class="mb-1.5 block text-sm font-medium text-gray-700">CSV File</label>
          <input
            ref="fileInput"
            type="file"
            accept=".csv"
            class="block w-full text-sm text-gray-600 file:mr-3 file:rounded-md file:border-0 file:bg-gray-100 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-gray-200"
            @change="onFileChange"
          />
        </div>
      </div>
    </template>
    <template #actions>
      <Button variant="solid" class="w-full" :disabled="!canSubmit()" @click="submit">Submit</Button>
    </template>
  </Dialog>
</template>
