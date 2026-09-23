<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
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
  /** fieldname -> what the student must do, for questions blocking submission. */
  issueMessages?: Map<string, string>
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

const showReview = ref(false)

function isBaseField(field: SchemaField) {
  return !CHANNEL_SUFFIXES.some((suffix) => field.fieldname.endsWith(suffix))
}

/** Empty HTML fields are Desk layout spacers; they'd render as nothing. */
function isRenderable(field: SchemaField) {
  if (field.fieldtype === 'HTML') return Boolean(field.options && field.options.replace(/<[^>]*>|&nbsp;|\s/g, ''))
  return true
}

const visibleColumns = computed(() =>
  props.section.columns.map((column) =>
    column.filter((f) => isBaseField(f) && isRenderable(f) && props.isFieldVisible(f)),
  ),
)
// A section whose every field is hidden or a spacer would be an empty card.
const hasContent = computed(() => visibleColumns.value.some((c) => c.length))

function hasReviewContentAnywhere() {
  return props.section.columns
    .flat()
    .filter(isBaseField)
    .some((f) => CHANNEL_SUFFIXES.some((suffix) => f.fieldname + suffix in props.doc))
}
</script>

<template>
  <div v-if="hasContent" class="rounded-lg border border-line bg-paper p-5">
    <div v-if="section.label || hasReviewContentAnywhere()" class="mb-4 flex items-center justify-between">
      <h3 v-if="section.label" class="text-sm font-semibold text-charcoal">{{ section.label }}</h3>
      <Button v-if="hasReviewContentAnywhere()" variant="ghost" size="sm" @click="showReview = !showReview">
        {{ showReview ? 'Hide review notes' : 'Show review notes' }}
      </Button>
    </div>

    <div class="grid gap-x-6 gap-y-4" :class="visibleColumns.filter((c) => c.length).length > 1 ? 'md:grid-cols-2' : ''">
      <template v-for="(column, ci) in visibleColumns" :key="ci">
        <div v-if="column.length" class="space-y-4">
          <div
            v-for="field in column"
            :id="`field-${field.fieldname}`"
            :key="field.fieldname"
            class="scroll-mt-24 rounded-md transition-shadow"
            :class="issueMessages?.has(field.fieldname) ? 'p-3 ring-2 ring-danger/60' : ''"
          >
            <SchemaFieldInput
              :field="field"
              :model-value="doc[field.fieldname]"
              :display-value="linkTitles?.[field.fieldname]"
              :disabled="disabled || Boolean(field.read_only)"
              :required="isFieldMandatory(field)"
              :docname="String(doc.name)"
              @update:model-value="(v) => emit('update', field.fieldname, v)"
            />
            <p v-if="issueMessages?.has(field.fieldname)" class="mt-1.5 flex items-center gap-1 text-xs font-medium text-danger">
              <FeatherIcon name="alert-circle" class="h-3.5 w-3.5 shrink-0" />
              {{ issueMessages.get(field.fieldname) }}
            </p>
            <ReviewChannel
              v-if="showReview"
              :base-fieldname="field.fieldname"
              :all-fields="allFields"
              :doc="doc"
              :disabled="disabled"
              @update="(fn, v) => emit('update', fn, v)"
            />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
