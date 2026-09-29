import { call } from './api'

// One lightweight COUNT query per doctype via Frappe's own generic,
// permission-respecting frappe.client.get_count — not a full record
// fetch, and run in parallel as a single batch (see useRecordCounts),
// not one-call-per-render.
const MANAGED_DOCTYPES = [
  'Academic Organizational Unit',
  'IRB Unit',
  'IRB Project',
  'Faculty',
  'Student',
  'Faculty Academic Organizational Unit',
  'Student Project Mapping',
] as const

export type ManagedDoctype = (typeof MANAGED_DOCTYPES)[number]

export async function fetchRecordCounts(): Promise<Record<ManagedDoctype, number>> {
  const counts = await Promise.all(MANAGED_DOCTYPES.map((doctype) => call<number>('frappe.client.get_count', { doctype })))
  return Object.fromEntries(MANAGED_DOCTYPES.map((doctype, i) => [doctype, counts[i]])) as Record<
    ManagedDoctype,
    number
  >
}
