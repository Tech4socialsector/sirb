<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import AttachField from './AttachField.vue'
import type { SchemaField } from '@/types/schema'

const props = defineProps<{
  field: SchemaField
  modelValue: unknown
  displayValue?: string | null
  disabled: boolean
  required: boolean
  /** Name of the IRB Project — Attach fields upload onto it. */
  docname?: string
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
    case 'Float':
      return 'number'
    case 'Date':
      return 'date'
    default:
      return 'text'
  }
})

const selectOptions = computed(() => {
  if (props.field.fieldtype !== 'Select' || !props.field.options) return []
  return props.field.options.split('\n').map((value) => ({ label: value || 'Select…', value }))
})

// Frappe stores Check as 0/1; the checkbox wants a boolean.
const controlValue = computed(() => (props.field.fieldtype === 'Check' ? Boolean(Number(props.modelValue)) : props.modelValue))

/** Emit values in the shape Frappe stores for each fieldtype, so an
 * untouched field never looks "changed" and bad input is never saved. */
function onInput(value: unknown) {
  switch (props.field.fieldtype) {
    case 'Check':
      return emit('update:modelValue', value ? 1 : 0)
    case 'Int': {
      const text = String(value ?? '').trim()
      const n = Number.parseInt(text, 10)
      return emit('update:modelValue', text === '' || Number.isNaN(n) ? null : n)
    }
    case 'Float': {
      const text = String(value ?? '').trim()
      const n = Number.parseFloat(text)
      return emit('update:modelValue', text === '' || Number.isNaN(n) ? null : n)
    }
    case 'Date':
      return emit('update:modelValue', value ? String(value) : null)
    default:
      return emit('update:modelValue', value)
  }
}
</script>

<template>
  <!-- HTML fields are DocType-authored static content (IRB policy, the
       student declaration, section headings) — show it, never an input.
       Empty ones are layout spacers in Desk and render nothing here. -->
  <div
    v-if="field.fieldtype === 'HTML'"
    class="sirb-html-block text-sm text-charcoal"
    v-html="field.options"
  />
  <AttachField
    v-else-if="field.fieldtype === 'Attach'"
    :label="field.label || undefined"
    :description="field.description || undefined"
    :model-value="modelValue"
    :required="required"
    :disabled="disabled"
    doctype="IRB Project"
    :docname="docname"
    :fieldname="field.fieldname"
    @update:model-value="(v) => emit('update:modelValue', v)"
  />
  <div v-else-if="isLink">
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
    :model-value="controlValue"
    @update:model-value="onInput"
  />
</template>
