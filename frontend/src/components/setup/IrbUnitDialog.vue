<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Autocomplete, Button, Checkbox, Dialog, ErrorMessage, FeatherIcon, FormControl, FormLabel } from 'frappe-ui'
import { saveIrbUnit } from '@/services/setup'
import type { OrgTreeIndex } from '@/utils/orgTree'
import type { FacultyMembership, FacultyRow, IrbUnitRow } from '@/types/setup'

/** One row of the committee table: a person, plus the membership row
 * that links them to the committee (absent until saved for new people). */
interface CommitteeRow {
  faculty: string
  membership?: string
}

const props = defineProps<{
  modelValue: boolean
  /** IRB Unit being edited; omit to create. */
  irbUnit?: IrbUnitRow | null
  /** Pre-selected Academic Organizational Unit when creating. */
  aoUnit?: string | null
  index: OrgTreeIndex
  irbUnits: IrbUnitRow[]
  memberships: FacultyMembership[]
  faculty: FacultyRow[]
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [string] }>()

const form = ref({ ao_unit: '', num_reviewers: '1' as '1' | '2', mentor_required: true, committee: [] as CommitteeRow[] })
const saving = ref(false)
const error = ref('')
const notice = ref('')

const isEdit = computed(() => !!props.irbUnit)
const unitLocked = computed(() => isEdit.value && (props.irbUnit?.project_count ?? 0) > 0)
const membershipByName = computed(() => new Map(props.memberships.map((m) => [m.name, m])))
const facultyByName = computed(() => new Map(props.faculty.map((f) => [String(f.name), f])))

const takenUnits = computed(
  () => new Set(props.irbUnits.filter((u) => u.name !== props.irbUnit?.name).map((u) => u.ao_unit)),
)

const unitOptions = computed(() => [
  { label: 'Select a unit…', value: '', disabled: true },
  ...props.index.ordered.map((u) => ({
    label: `${props.index.path(u.name)}${takenUnits.value.has(u.name) ? ' (has IRB Unit)' : ''}`,
    value: u.name,
    disabled: takenUnits.value.has(u.name),
  })),
])

/** Read-only, like Desk's fetched "School/Programme" field. */
const programmeName = computed(() => props.index.byName.get(form.value.ao_unit)?.ao_name || '')

function facultyName(id: string) {
  const f = facultyByName.value.get(id)
  return f?.full_name || `Faculty ${id}`
}

/** "Name (Unit)" — the same title Desk shows in the committee table. */
function rowLabel(row: CommitteeRow) {
  const m = row.membership ? membershipByName.value.get(row.membership) : undefined
  const unit = m?.unit_name || props.index.byName.get(form.value.ao_unit)?.ao_name
  return unit ? `${facultyName(row.faculty)} (${unit})` : facultyName(row.faculty)
}

function rowStatus(row: CommitteeRow) {
  if (!row.membership) return 'new'
  return membershipByName.value.get(row.membership)?.status === 'inactive' ? 'inactive' : 'active'
}

// Faculty picker: people already in this unit (or its sub-units) first,
// then everyone else. Anyone already on the committee, or without a login
// (the server would reject them), is left out.
const pickerOptions = computed(() => {
  const inCommittee = new Set(form.value.committee.map((r) => r.faculty))
  const scope = form.value.ao_unit ? props.index.subtree(form.value.ao_unit) : new Set<string>()
  const unitsByFaculty = new Map<string, string[]>()
  const inScope = new Set<string>()
  for (const m of props.memberships) {
    const id = String(m.faculty_member)
    if (!unitsByFaculty.has(id)) unitsByFaculty.set(id, [])
    unitsByFaculty.get(id)!.push(m.unit_name || m.ao_unit)
    if (scope.has(m.ao_unit)) inScope.add(id)
  }
  const toOption = (f: FacultyRow) => ({
    label: f.full_name || `Faculty ${f.name}`,
    value: String(f.name),
    description: [f.system_user, (unitsByFaculty.get(String(f.name)) || []).join(', ')].filter(Boolean).join(' · '),
  })
  const available = props.faculty.filter((f) => f.system_user && !inCommittee.has(String(f.name)))
  const here = available.filter((f) => inScope.has(String(f.name))).map(toOption)
  const others = available.filter((f) => !inScope.has(String(f.name))).map(toOption)
  return [
    ...(here.length ? [{ group: 'In this unit', items: here }] : []),
    ...(others.length ? [{ group: here.length ? 'Other faculty' : 'All faculty', items: others }] : []),
  ]
})
const pickerEmpty = computed(() => pickerOptions.value.every((g) => !g.items.length))

function addFaculty(option: { value: string | number } | null) {
  if (!option) return
  const faculty = String(option.value)
  if (form.value.committee.some((r) => r.faculty === faculty)) return
  // Reuse their membership of this unit if one exists; the server does the
  // same lookup (and creates one when missing) on save.
  const existing = props.memberships.find((m) => String(m.faculty_member) === faculty && m.ao_unit === form.value.ao_unit)
  form.value.committee = [...form.value.committee, { faculty, membership: existing?.name }]
}

function removeRow(i: number) {
  form.value.committee = form.value.committee.filter((_, idx) => idx !== i)
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    error.value = ''
    notice.value = ''
    if (props.irbUnit) {
      // Build one row per person. Rows whose membership was deleted, and
      // repeats of the same person (Desk used to allow those), are dropped
      // here and fixed for good on the next save.
      const rows: CommitteeRow[] = []
      let dropped = 0
      for (const name of props.irbUnit.members) {
        const m = membershipByName.value.get(name)
        const faculty = m ? String(m.faculty_member) : ''
        if (!faculty || rows.some((r) => r.faculty === faculty)) {
          dropped++
          continue
        }
        rows.push({ faculty, membership: name })
      }
      if (dropped)
        notice.value = `${dropped} duplicate or missing committee ${dropped === 1 ? 'entry was' : 'entries were'} removed. Save to apply.`
      form.value = {
        ao_unit: props.irbUnit.ao_unit,
        num_reviewers: props.irbUnit.num_reviewers === '2' ? '2' : '1',
        mentor_required: !!props.irbUnit.mentor_required,
        committee: rows,
      }
    } else {
      const preset = props.aoUnit && !takenUnits.value.has(props.aoUnit) ? props.aoUnit : ''
      form.value = { ao_unit: preset, num_reviewers: '1', mentor_required: true, committee: [] }
    }
  },
)

// People added without a membership of the chosen unit yet: when the unit
// changes, re-point them at their membership of the new unit (if any).
watch(
  () => form.value.ao_unit,
  (unit) => {
    form.value.committee = form.value.committee.map((r) => {
      if (r.membership && membershipByName.value.get(r.membership)) return r
      const m = props.memberships.find((x) => String(x.faculty_member) === r.faculty && x.ao_unit === unit)
      return { faculty: r.faculty, membership: m?.name }
    })
  },
)

async function submit() {
  if (saving.value) return
  error.value = !form.value.ao_unit ? 'Select an Academic Organizational Unit.' : ''
  if (error.value) return
  saving.value = true
  try {
    const name = await saveIrbUnit({
      name: props.irbUnit?.name,
      ao_unit: form.value.ao_unit,
      mentor_required: form.value.mentor_required,
      num_reviewers: form.value.num_reviewers,
      members: form.value.committee.map((r) => ({ faculty: r.faculty, membership: r.membership })),
    })
    emit('saved', name)
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Could not save the IRB Unit.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :model-value="modelValue"
    :options="{ title: isEdit ? irbUnit?.ao_name || 'IRB Unit' : 'New IRB Unit', size: '2xl' }"
    @update:model-value="(v: boolean) => !saving && emit('update:modelValue', v)"
  >
    <template #body-content>
      <div class="sirb-fill-select space-y-4">
        <div>
          <FormControl
            v-model="form.ao_unit"
            type="select"
            label="Academic Organizational Unit"
            :options="unitOptions"
            :disabled="unitLocked"
            required
          />
          <p v-if="unitLocked" class="mt-1.5 text-xs text-muted">
            Locked: {{ irbUnit!.project_count }} project(s) already belong to this IRB Unit.
          </p>
        </div>

        <FormControl :model-value="programmeName" type="text" label="School/Programme" disabled />

        <FormControl
          v-model="form.num_reviewers"
          type="select"
          label="Number of IRB Reviewers for a project"
          :options="[
            { label: '1', value: '1' },
            { label: '2', value: '2' },
          ]"
        />

        <Checkbox v-model="form.mentor_required" label="Mentor Required" />

        <div class="space-y-2">
          <FormLabel label="IRB Committee Faculty Members" />
          <div class="overflow-hidden rounded-lg border border-line">
            <table class="w-full text-left text-sm">
              <thead class="bg-canvas text-xs text-muted">
                <tr>
                  <th class="w-14 px-3 py-2 font-medium">No.</th>
                  <th class="px-3 py-2 font-medium">Faculty Member</th>
                  <th class="w-12 px-3 py-2" />
                </tr>
              </thead>
              <tbody class="divide-y divide-line">
                <tr v-if="!form.committee.length">
                  <td colspan="3" class="px-3 py-4 text-center text-sm text-muted">No committee members yet.</td>
                </tr>
                <tr v-for="(row, i) in form.committee" :key="row.faculty">
                  <td class="px-3 py-2 text-muted">{{ i + 1 }}</td>
                  <td class="px-3 py-2">
                    <span class="text-charcoal">{{ rowLabel(row) }}</span>
                    <span
                      v-if="rowStatus(row) === 'inactive'"
                      class="ml-2 rounded-full bg-canvas px-2 py-0.5 text-[11px] font-medium text-muted"
                      >Inactive</span
                    >
                    <span
                      v-else-if="rowStatus(row) === 'new'"
                      class="ml-2 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-info"
                      title="They'll be added as a member of this unit when you save."
                      >New to unit</span
                    >
                  </td>
                  <td class="px-3 py-2 text-right">
                    <button
                      type="button"
                      class="rounded-md p-1 text-muted hover:bg-canvas hover:text-danger"
                      :aria-label="`Remove ${facultyName(row.faculty)}`"
                      @click="removeRow(i)"
                    >
                      <FeatherIcon name="x" class="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="max-w-sm">
            <Autocomplete
              :options="pickerOptions"
              :model-value="null"
              :placeholder="pickerEmpty ? 'No more faculty to add' : 'Add Row — search faculty…'"
              @update:model-value="addFaculty"
            />
          </div>
        </div>

        <p v-if="notice" class="text-sm text-info">{{ notice }}</p>

        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="saving" @click="emit('update:modelValue', false)">Cancel</Button>
        <Button variant="solid" :loading="saving" @click="submit">{{ isEdit ? 'Save' : 'Create New' }}</Button>
      </div>
    </template>
  </Dialog>
</template>
