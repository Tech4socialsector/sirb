<script setup lang="ts">
import { ref } from 'vue'
import { Button } from 'frappe-ui'
import SchemaFieldInput from './SchemaFieldInput.vue'
import ReviewChannel from './ReviewChannel.vue'
import type { SchemaField, SchemaSection } from '@/types/schema'
import type { IrbProjectDoc } from '@/types/project'

const CHANNEL_SUFFIXES = ['_sc', '_mf', '_rf', '_prn', '_srn', '_fc']

const props = defineProps<{
  section: SchemaSection
  allFields: SchemaField[]
  doc: IrbProjectDoc
  linkTitles?: Record<string, string>
  disabled: boolean
  isFieldVisible: (field: SchemaField) => boolean
  isFieldMandatory: (field: SchemaField) => boolean
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const showReview = ref(false)

function isBaseField(field: SchemaField) {
  return !CHANNEL_SUFFIXES.some((suffix) => field.fieldname.endsWith(suffix))
}

function hasReviewContentAnywhere() {
  return props.section.columns
    .flat()
    .filter(isBaseField)
    .some((f) => CHANNEL_SUFFIXES.some((suffix) => f.fieldname + suffix in props.doc))
}
</script>

<template>
  <div class="rounded-lg border border-line bg-paper p-5">
    <div class="mb-4 flex items-center justify-between">
      <h3 v-if="section.label" class="text-sm font-semibold text-charcoal">{{ section.label }}</h3>
      <Button v-if="hasReviewContentAnywhere()" variant="ghost" size="sm" @click="showReview = !showReview">
        {{ showReview ? 'Hide review notes' : 'Show review notes' }}
      </Button>
    </div>

    <div class="grid gap-x-6 gap-y-4" :class="section.columns.length > 1 ? 'md:grid-cols-2' : ''">
      <div v-for="(column, ci) in section.columns" :key="ci" class="space-y-4">
        <template v-for="field in column.filter(isBaseField)" :key="field.fieldname">
          <div v-if="isFieldVisible(field)">
            <SchemaFieldInput
              :field="field"
              :model-value="doc[field.fieldname]"
              :display-value="linkTitles?.[field.fieldname]"
              :disabled="disabled || Boolean(field.read_only)"
              :required="isFieldMandatory(field)"
              @update:model-value="(v) => emit('update', field.fieldname, v)"
            />
            <ReviewChannel
              v-if="showReview"
              :base-fieldname="field.fieldname"
              :all-fields="allFields"
              :doc="doc"
              :disabled="disabled"
              @update="(fn, v) => emit('update', fn, v)"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
