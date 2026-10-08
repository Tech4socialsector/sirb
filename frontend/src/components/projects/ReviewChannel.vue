<script setup lang="ts">
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import type { SchemaField } from '@/types/schema'
import type { FieldChangeEntry, IrbProjectDoc } from '@/types/project'

// The review section of a question, laid out as on the Desk form
// (`<section>_addons` in irb_project.json): the student's, mentor's and
// reviewer's channels on the left; the reviewers' notes to each other and
// the question's field changes on the right. Labels come from the schema.
const COLUMNS: { suffix: string; fallback: string }[][] = [
  [
    { suffix: '_sc', fallback: 'Talk to your reviewer' },
    { suffix: '_mf', fallback: 'Mentor Feedback' },
    { suffix: '_rf', fallback: 'Reviewer feedback to student' },
  ],
  [
    { suffix: '_prn', fallback: 'Primary reviewer draft comments (to secondary reviewer)' },
    { suffix: '_srn', fallback: 'Secondary Reviewer Notes' },
    { suffix: '_fc', fallback: 'Field Changes' },
  ],
]

const props = defineProps<{
  baseFieldname: string
  sectionLabel?: string | null
  /** The question's own fields, for the Field Changes summary. */
  sectionFields: SchemaField[]
  allFields: SchemaField[]
  doc: IrbProjectDoc
  disabled: boolean
  /** Presence in the doc (the server leaves out what this user may not
   * see) and the field's depends_on — e.g. reviewer notes only on
   * two-reviewer projects. */
  isFieldVisible: (field: SchemaField) => boolean
  /** Fields others changed since this user last had the project. */
  changedFields?: ReadonlySet<string>
  /** What those changes were (sirb_api.project.get_review_highlights). */
  fieldChanges?: Record<string, FieldChangeEntry[]>
  /** Permlevels this user may save; absent means no restriction known. */
  writableLevels?: ReadonlySet<number>
}>()

const emit = defineEmits<{ update: [fieldname: string, value: unknown] }>()

function plain(value: unknown) {
  return String(value ?? '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

// Field Changes is shown only, never saved — the Desk form fills it the same
// way. Falls back to whatever is stored when nothing changed this round.
const fieldChangesText = computed(() => {
  const lines: string[] = []
  for (const field of props.sectionFields) {
    for (const change of props.fieldChanges?.[field.fieldname] || [])
      lines.push(
        `${field.label || field.fieldname} changed from "${plain(change.old_value)}" to "${plain(change.new_value)}" on ${change.date}`,
      )
  }
  return lines.join('\n')
})

const columns = computed(() =>
  COLUMNS.map((column) =>
    column
      .map(({ suffix, fallback }) => {
        const fieldname = props.baseFieldname + suffix
        const field = props.allFields.find((f) => f.fieldname === fieldname)
        if (!field || !props.isFieldVisible(field)) return null
        const isFieldChanges = suffix === '_fc'
        return {
          fieldname,
          label: field.label || fallback,
          value: isFieldChanges ? fieldChangesText.value || props.doc[fieldname] : props.doc[fieldname],
          changed: !isFieldChanges && Boolean(props.changedFields?.has(fieldname)),
          // Frappe drops edits to permlevels the user can't write, so don't
          // offer them; Field Changes is never edited.
          readOnly:
            isFieldChanges ||
            Boolean(field.read_only) ||
            (props.writableLevels ? !props.writableLevels.has(field.permlevel) : false),
        }
      })
      .filter((c): c is NonNullable<typeof c> => Boolean(c)),
  ).filter((column) => column.length),
)
</script>

<template>
  <div v-if="columns.length" class="mt-3 rounded-md border border-line bg-canvas p-4">
    <h4 v-if="sectionLabel" class="mb-3 text-sm font-semibold text-charcoal">{{ sectionLabel }} - review</h4>
    <div class="grid gap-x-6 gap-y-3" :class="columns.length > 1 ? 'md:grid-cols-2' : ''">
      <div v-for="(column, ci) in columns" :key="ci" class="space-y-3">
        <div
          v-for="channel in column"
          :id="`field-${channel.fieldname}`"
          :key="channel.fieldname"
          class="rounded-md"
          :class="channel.changed ? 'bg-amber-50 p-2 ring-2 ring-amber-300' : ''"
        >
          <p v-if="channel.changed" class="mb-1 text-xs font-semibold text-amber-800">New since you last had this project</p>
          <FormControl
            type="textarea"
            :label="channel.label"
            :disabled="disabled || channel.readOnly"
            :model-value="channel.value"
            @update:model-value="(v: unknown) => emit('update', channel.fieldname, v)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
