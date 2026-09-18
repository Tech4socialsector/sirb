<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import type { SchemaField } from '@/types/schema'
import type { IrbProjectDoc } from '@/types/project'

const CHANNEL_SUFFIXES: Record<string, string> = {
  _sc: 'Talk to your reviewer',
  _mf: 'Mentor feedback',
  _rf: 'Reviewer feedback to student',
  _prn: 'Primary reviewer notes (to secondary reviewer)',
  _srn: 'Secondary reviewer notes',
}

const props = defineProps<{
  baseFieldname: string
  allFields: SchemaField[]
  doc: IrbProjectDoc
  disabled: boolean
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const channels = computed(() => {
  return Object.entries(CHANNEL_SUFFIXES)
    .map(([suffix, label]) => {
      const fieldname = props.baseFieldname + suffix
      const field = props.allFields.find((f) => f.fieldname === fieldname)
      // Server only includes a field in the doc payload when the current
      // user has permlevel read access to it — absence means "not visible
      // to me", not "empty".
      if (!field || !(fieldname in props.doc)) return null
      return { fieldname, label, field, value: props.doc[fieldname] }
    })
    .filter((c): c is NonNullable<typeof c> => Boolean(c))
})
</script>

<template>
  <div v-if="channels.length" class="mt-2 space-y-3 rounded-md border border-gray-100 bg-gray-50 p-3">
    <div v-for="channel in channels" :key="channel.fieldname">
      <FormControl
        type="textarea"
        :label="channel.label"
        :disabled="disabled || Boolean(channel.field.read_only)"
        :model-value="channel.value"
        @update:model-value="(v: unknown) => emit('update', channel.fieldname, v)"
      />
    </div>
  </div>
</template>
