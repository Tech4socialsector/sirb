import { computed, ref, type Ref } from 'vue'
import { fetchProjectSchema } from '@/services/schema'
import type { ProjectSchema, SchemaField, SchemaSection, SchemaTab } from '@/types/schema'
import type { IrbProjectDoc } from '@/types/project'

function groupIntoTabs(schema: ProjectSchema): SchemaTab[] {
  const orderedFields = schema.field_order
    .map((name) => schema.fields.find((f) => f.fieldname === name))
    .filter((f): f is SchemaField => Boolean(f))

  const tabs: SchemaTab[] = []
  let currentTab: SchemaTab | null = null
  let currentSection: SchemaSection | null = null
  let currentColumn: SchemaField[] = []

  function pushSection() {
    if (currentSection && currentTab) {
      currentSection.columns.push(currentColumn)
      currentTab.sections.push(currentSection)
    }
    currentSection = null
    currentColumn = []
  }

  function pushTab() {
    pushSection()
    if (currentTab) tabs.push(currentTab)
    currentTab = null
  }

  for (const field of orderedFields) {
    if (field.fieldtype === 'Tab Break') {
      pushTab()
      currentTab = { fieldname: field.fieldname, label: field.label || field.fieldname, sections: [] }
      continue
    }
    if (!currentTab) {
      currentTab = { fieldname: '__default__', label: '', sections: [] }
    }
    if (field.fieldtype === 'Section Break') {
      pushSection()
      currentSection = { fieldname: field.fieldname, label: field.label, depends_on: field.depends_on, columns: [] }
      continue
    }
    if (field.fieldtype === 'Column Break') {
      if (currentSection) {
        currentSection.columns.push(currentColumn)
        currentColumn = []
      }
      continue
    }
    if (!currentSection) {
      currentSection = { fieldname: '__default__', label: null, columns: [] }
    }
    currentColumn.push(field)
  }
  pushTab()

  return tabs
}

/**
 * Evaluates the subset of Frappe's `eval:` depends_on expressions actually
 * used by IRB Project (doc.<field> comparisons, .includes(...) checks, and
 * boolean combinations) against the current in-memory doc. This is a
 * conservative expression evaluator, not a general JS sandbox — it only
 * understands the shapes these expressions are written in.
 */
export function evalDependsOn(expr: string | null, doc: Record<string, unknown>): boolean {
  if (!expr) return true
  let e = expr.trim()
  if (e.startsWith('eval:')) e = e.slice(5).trim()

  try {
    // eslint-disable-next-line @typescript-eslint/no-implied-eval
    const fn = new Function(
      'doc',
      'frappe',
      `"use strict"; return (${e});`,
    )
    const frappeStub = {
      user: 'sirb-frontend-user',
      has_role: () => false,
    }
    return Boolean(fn(doc, frappeStub))
  } catch {
    return true
  }
}

export function useProjectSchema(doc: Ref<IrbProjectDoc | null>) {
  const schema = ref<ProjectSchema | null>(null)
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      schema.value = await fetchProjectSchema()
    } finally {
      loading.value = false
    }
  }

  const tabs = computed<SchemaTab[]>(() => (schema.value ? groupIntoTabs(schema.value) : []))

  function isFieldVisible(field: SchemaField): boolean {
    if (!doc.value) return false
    return evalDependsOn(field.depends_on, doc.value)
  }

  function isFieldMandatory(field: SchemaField): boolean {
    if (field.reqd) return true
    if (!field.mandatory_depends_on || !doc.value) return false
    return evalDependsOn(field.mandatory_depends_on, doc.value)
  }

  function isSectionVisible(section: SchemaSection): boolean {
    if (!doc.value) return false
    return evalDependsOn(section.depends_on ?? null, doc.value)
  }

  function isTabVisible(tab: SchemaTab): boolean {
    if (!doc.value) return false
    if (tab.fieldname === 'basic_details_tab') return true
    if (tab.fieldname === 'human_ethics_questionnaire_tab') {
      return ['Humans', 'BOTH Humans AND Non Humans'].includes(String(doc.value.project_domain))
    }
    if (tab.fieldname === 'animal_ethics_questionnaire_tab') {
      return ['Non Human Species', 'BOTH Humans AND Non Humans'].includes(String(doc.value.project_domain))
    }
    return true
  }

  return { schema, tabs, loading, load, isFieldVisible, isFieldMandatory, isSectionVisible, isTabVisible }
}
