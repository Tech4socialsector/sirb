<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Autocomplete, FormLabel } from 'frappe-ui'
import { searchLink, type LinkOption } from '@/services/links'

const props = defineProps<{
  doctype: string
  label: string
  modelValue: string | undefined | null
  required?: boolean
  /** Title of the current value (e.g. a Faculty's full name), shown until
   * the options containing it have loaded. */
  displayValue?: string | null
  /** Show a "Clear" button so an optional link can be emptied. */
  clearable?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [string | undefined] }>()

const options = ref<LinkOption[]>([])

async function onQuery(txt: string) {
  options.value = await searchLink(props.doctype, txt)
}

// frappe-ui's Autocomplete only emits `update:query` when the typed text
// changes, never on initial mount — so without this, `options` stays
// empty (showing "No results found") until the user types at least one
// character, even though matching records exist.
onMounted(() => onQuery(''))

// Keep the picked option's title (e.g. the IRB Unit's name) so the input
// doesn't fall back to showing the record's raw ID once a value is chosen.
const selected = ref<LinkOption | undefined>()

const selectedOption = computed<LinkOption | undefined>(() => {
  if (!props.modelValue) return undefined
  if (selected.value?.value === props.modelValue) return selected.value
  return (
    options.value.find((o) => o.value === props.modelValue) ?? {
      value: props.modelValue,
      label: props.displayValue || props.modelValue,
    }
  )
})

function onChange(option: LinkOption | undefined) {
  selected.value = option
  emit('update:modelValue', option?.value)
}
</script>

<template>
  <div class="space-y-1.5">
    <FormLabel :label="label" :required="required" />
    <Autocomplete
      :options="options"
      :model-value="selectedOption"
      placeholder="Search…"
      :show-footer="clearable"
      @update:query="onQuery"
      @update:model-value="onChange"
    />
  </div>
</template>
