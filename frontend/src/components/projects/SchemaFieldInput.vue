<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import type { SchemaField } from '@/types/schema'

const props = defineProps<{
  field: SchemaField
  modelValue: unknown
  disabled: boolean
  required: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [unknown] }>()

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
  <FormControl
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
