<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import type { SchemaField } from '@/types/schema'

const props = defineProps<{
  field: SchemaField
  modelValue: unknown
  displayValue?: string | null
  disabled: boolean
  required: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [unknown] }>()

// Link fields hold IDs (e.g. Faculty's autoincrement name "8"), never the
// human-readable title. Editing one via free text here can't reliably point
// at a valid record, so it's shown read-only using its resolved title.
const isLink = computed(() => props.field.fieldtype === 'Link')

const controlType = computed(() => {
  switch (props.field.fieldtype) {
    case 'Select':
      return 'select'
    case 'Check':
      return 'checkbox'
    case 'Small Text':
    case 'Text':
    case 'Long Text':
      return 'textarea'
    case 'Int':
      return 'number'
    case 'Date':
      return 'date'
    default:
      return 'text'
  }
})

const selectOptions = computed(() => {
  if (props.field.fieldtype !== 'Select' || !props.field.options) return []
  return props.field.options.split('\n').map((value) => ({ label: value, value }))
})

function onInput(value: unknown) {
  emit('update:modelValue', value)
}
</script>

<template>
  <div v-if="isLink">
    <label v-if="field.label" class="mb-1.5 block text-sm text-charcoal">{{ field.label }}</label>
    <p class="truncate rounded-md border border-line bg-canvas px-2.5 py-1.5 text-sm text-charcoal">
      {{ displayValue || modelValue || 'Not set' }}
    </p>
  </div>
  <FormControl
    v-else
    :type="controlType"
    :label="field.label || undefined"
    :description="field.description || undefined"
    :disabled="disabled"
    :required="required"
    :options="controlType === 'select' ? selectOptions : undefined"
    :model-value="modelValue"
    @update:model-value="onInput"
  />
</template>
