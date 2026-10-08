<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import SchemaFieldInput from './SchemaFieldInput.vue'
import ReviewChannel from './ReviewChannel.vue'
import type { SchemaField, SchemaSection } from '@/types/schema'
import type { FieldChangeEntry, IrbProjectDoc } from '@/types/project'

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
  /** Fields this user may edit even when the form is `disabled` or the
   * field is read-only (admins: status, mentor and reviewers). */
  overrideEditable?: ReadonlySet<string>
  /** Fields others changed since this user last had the project. */
  changedFields?: ReadonlySet<string>
  /** Permlevels this user may save; absent means no restriction known. */
  writableLevels?: ReadonlySet<number>
  /** What others changed (sirb_api.project.get_review_highlights). */
  fieldChanges?: Record<string, FieldChangeEntry[]>
  /** Set by "Toggle All Sections": open (true) or close (false) every
   * review section; null until it's first used. */
  allReviewsOpen?: boolean | null
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

// Frappe drops edits to permlevels the user can't write, so don't offer them.
function canWrite(field: SchemaField) {
  return !props.writableLevels || props.writableLevels.has(field.permlevel)
}

function isFieldDisabled(field: SchemaField) {
  if (props.overrideEditable?.has(field.fieldname)) return false
  return props.disabled || Boolean(field.read_only) || !canWrite(field)
}

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

// Review notes belong to a whole question section and are named after it
// (section `heq_s1` -> `heq_s1_rf`, `heq_s1_mf`, …), as in the Desk form.
// Only the channels ReviewChannel shows count; `_fc` isn't one of them.
const REVIEW_SUFFIXES = ['_sc', '_mf', '_rf', '_prn', '_srn']
// The server leaves out the channels this user may not read, and some only
// apply to some projects (reviewer notes need two reviewers).
const hasReviewContent = computed(() =>
  REVIEW_SUFFIXES.some((suffix) => {
    const field = props.allFields.find((f) => f.fieldname === props.section.fieldname + suffix)
    return Boolean(field && props.isFieldVisible(field))
  }),
)
const sectionFields = computed(() => props.section.columns.flat().filter(isBaseField))

// New review notes (e.g. reviewer feedback for a student) open by themselves,
// so they can't be missed behind the "Show review notes" button.
const hasNewNotes = computed(() =>
  REVIEW_SUFFIXES.some((suffix) => props.changedFields?.has(props.section.fieldname + suffix)),
)
const showReview = ref(hasNewNotes.value || props.allReviewsOpen === true)
watch(hasNewNotes, (isNew) => {
  if (isNew) showReview.value = true
})
watch(
  () => props.allReviewsOpen,
  (open) => {
    if (open !== null && open !== undefined) showReview.value = open
  },
)
</script>

<template>
  <div v-if="hasContent || hasReviewContent" class="rounded-lg border border-line bg-paper p-5">
    <div v-if="section.label" class="mb-4">
      <h3 class="text-sm font-semibold text-charcoal">{{ section.label }}</h3>
    </div>

    <div class="grid gap-x-6 gap-y-4" :class="visibleColumns.filter((c) => c.length).length > 1 ? 'md:grid-cols-2' : ''">
      <template v-for="(column, ci) in visibleColumns" :key="ci">
        <div v-if="column.length" class="space-y-4">
          <div
            v-for="field in column"
            :id="`field-${field.fieldname}`"
            :key="field.fieldname"
            class="scroll-mt-24 rounded-md transition-shadow"
            :class="
              issueMessages?.has(field.fieldname)
                ? 'p-3 ring-2 ring-danger/60'
                : changedFields?.has(field.fieldname)
                  ? 'bg-amber-50 p-3 ring-2 ring-amber-300'
                  : ''
            "
          >
            <p v-if="changedFields?.has(field.fieldname)" class="mb-1 text-xs font-semibold text-amber-800">
              Changed since you last had this project
            </p>
            <SchemaFieldInput
              :field="field"
              :model-value="doc[field.fieldname]"
              :display-value="linkTitles?.[field.fieldname]"
              :disabled="isFieldDisabled(field)"
              :editable-link="overrideEditable?.has(field.fieldname)"
              :required="isFieldMandatory(field)"
              :docname="String(doc.name)"
              @update:model-value="(v) => emit('update', field.fieldname, v)"
            />
            <p v-if="issueMessages?.has(field.fieldname)" class="mt-1.5 flex items-center gap-1 text-xs font-medium text-danger">
              <FeatherIcon name="alert-circle" class="h-3.5 w-3.5 shrink-0" />
              {{ issueMessages.get(field.fieldname) }}
            </p>
          </div>
        </div>
      </template>
    </div>

    <!-- Below the question, as on the Desk form. -->
    <div v-if="hasReviewContent" class="mt-4 flex flex-wrap items-center gap-2">
      <Button variant="subtle" size="sm" :aria-expanded="showReview" @click="showReview = !showReview">
        Show/Hide Review Section
      </Button>
      <span v-if="hasNewNotes" class="rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">New review notes</span>
    </div>

    <ReviewChannel
      v-if="hasReviewContent && showReview"
      :base-fieldname="section.fieldname"
      :section-label="section.label"
      :section-fields="sectionFields"
      :all-fields="allFields"
      :doc="doc"
      :disabled="disabled"
      :is-field-visible="isFieldVisible"
      :changed-fields="changedFields"
      :field-changes="fieldChanges"
      :writable-levels="writableLevels"
      @update="(fn, v) => emit('update', fn, v)"
    />
  </div>
</template>
