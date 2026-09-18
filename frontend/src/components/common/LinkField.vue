<script setup lang="ts">
import { ref } from 'vue'
import { Autocomplete, FormLabel } from 'frappe-ui'
import { searchLink, type LinkOption } from '@/services/links'

const props = defineProps<{
  doctype: string
  label: string
  modelValue: string | undefined
  required?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [string | undefined] }>()

const options = ref<LinkOption[]>([])

async function onQuery(txt: string) {
  options.value = await searchLink(props.doctype, txt)
}

function onChange(option: LinkOption | undefined) {
  emit('update:modelValue', option?.value)
}
</script>

<template>
  <div class="space-y-1.5">
    <FormLabel :label="label" :required="required" />
    <Autocomplete
      :options="options"
      :model-value="modelValue ? { value: modelValue, label: modelValue } : undefined"
      placeholder="Search…"
      @update:query="onQuery"
      @update:model-value="onChange"
    />
  </div>
</template>
