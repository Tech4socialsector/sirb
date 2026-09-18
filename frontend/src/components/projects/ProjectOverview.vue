<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import type { IrbProjectDoc } from '@/types/project'

const props = defineProps<{ doc: IrbProjectDoc; disabled: boolean }>()
const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const domainOptions = [
  { label: '-- Select --', value: '-- Select --' },
  { label: 'IRB Not Required', value: 'IRB Not Required' },
  { label: 'Humans', value: 'Humans' },
  { label: 'Non Human Species', value: 'Non Human Species' },
  { label: 'BOTH Humans AND Non Humans', value: 'BOTH Humans AND Non Humans' },
]
</script>

<template>
  <div class="rounded-lg border border-gray-200 bg-white p-5">
    <h3 class="mb-4 text-sm font-semibold text-gray-900">Basic Project Details</h3>
    <div class="grid gap-4 md:grid-cols-2">
      <FormControl
        type="select"
        label="IRB Project Domain"
        :options="domainOptions"
        :disabled="disabled"
        :model-value="props.doc.project_domain"
        @update:model-value="(v: unknown) => emit('update', 'project_domain', v)"
      />
      <div />
      <FormControl
        type="textarea"
        label="Title"
        required
        :disabled="disabled"
        :model-value="props.doc.title"
        @update:model-value="(v: unknown) => emit('update', 'title', v)"
      />
      <FormControl
        type="textarea"
        label="Topic"
        required
        :disabled="disabled"
        :model-value="props.doc.topic"
        @update:model-value="(v: unknown) => emit('update', 'topic', v)"
      />
      <div class="md:col-span-2">
        <FormControl
          type="textarea"
          label="Abstract"
          required
          :disabled="disabled"
          :model-value="props.doc.abstract"
          @update:model-value="(v: unknown) => emit('update', 'abstract', v)"
        />
      </div>
    </div>
  </div>
</template>
