<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import type { IrbProjectDoc } from '@/types/project'

const props = defineProps<{ doc: IrbProjectDoc; disabled: boolean; issueMessages?: Map<string, string> }>()
const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const domainOptions = [
  { label: '-- Select --', value: '-- Select --' },
  { label: 'IRB Not Required', value: 'IRB Not Required' },
  { label: 'Humans', value: 'Humans' },
  { label: 'Non Human Species', value: 'Non Human Species' },
  { label: 'BOTH Humans AND Non Humans', value: 'BOTH Humans AND Non Humans' },
]

const textFields = [
  { fieldname: 'title', label: 'Title', wide: false },
  { fieldname: 'topic', label: 'Topic', wide: false },
  { fieldname: 'abstract', label: 'Abstract', wide: true },
]
</script>

<template>
  <div class="rounded-lg border border-line bg-paper p-5">
    <h3 class="mb-4 text-sm font-semibold text-charcoal">Basic Project Details</h3>
    <div class="grid gap-4 md:grid-cols-2">
      <div
        id="field-project_domain"
        class="scroll-mt-24 rounded-md"
        :class="issueMessages?.has('project_domain') ? 'p-3 ring-2 ring-danger/60' : ''"
      >
        <FormControl
          type="select"
          label="IRB Project Domain"
          :options="domainOptions"
          :disabled="disabled"
          :model-value="props.doc.project_domain"
          @update:model-value="(v: unknown) => emit('update', 'project_domain', v)"
        />
        <p v-if="issueMessages?.has('project_domain')" class="mt-1.5 text-xs font-medium text-danger">
          {{ issueMessages.get('project_domain') }}
        </p>
      </div>
      <div />
      <div
        v-for="f in textFields"
        :id="`field-${f.fieldname}`"
        :key="f.fieldname"
        class="scroll-mt-24 rounded-md"
        :class="[f.wide ? 'md:col-span-2' : '', issueMessages?.has(f.fieldname) ? 'p-3 ring-2 ring-danger/60' : '']"
      >
        <FormControl
          type="textarea"
          :label="f.label"
          required
          :disabled="disabled"
          :model-value="props.doc[f.fieldname]"
          @update:model-value="(v: unknown) => emit('update', f.fieldname, v)"
        />
        <p v-if="issueMessages?.has(f.fieldname)" class="mt-1.5 text-xs font-medium text-danger">
          {{ issueMessages.get(f.fieldname) }}
        </p>
      </div>
    </div>
  </div>
</template>
