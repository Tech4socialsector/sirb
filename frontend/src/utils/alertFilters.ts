import type { FilterOptions } from '@/types/admin'
import type { AlertFilters } from '@/types/alerts'

export const LIST_KEYS = ['campus', 'org_unit', 'irb_unit', 'academic_year', 'irb_cycle', 'status', 'faculty_mentor'] as const
export type ListKey = (typeof LIST_KEYS)[number]

/** Drop empty values and sort lists, so equal filters serialise equally. */
export function cleanFilters(f: AlertFilters): AlertFilters {
  if (f.mode === 'students') {
    // Kept even when empty: the server refuses an empty pick instead of
    // treating it as "no filter" (= every student).
    const out: AlertFilters = { mode: 'students', student: [...new Set((f.student ?? []).filter(Boolean))].sort() }
    const statuses = [...new Set((f.status ?? []).filter(Boolean))].sort()
    if (statuses.length) out.status = statuses
    return out
  }
  const out: AlertFilters = {}
  for (const k of LIST_KEYS) {
    const v = [...new Set((f[k] ?? []).filter(Boolean))].sort()
    if (v.length) out[k] = v
  }
  const days = Math.floor(Number(f.inactive_days) || 0)
  if (days > 0) out.inactive_days = days
  return out
}

export function filtersKey(f: AlertFilters) {
  return JSON.stringify(cleanFilters(f))
}

const LABELS: Record<ListKey, string> = {
  campus: 'Campus',
  org_unit: 'Unit',
  irb_unit: 'Programme',
  academic_year: 'Year',
  irb_cycle: 'Cycle',
  status: 'Status',
  faculty_mentor: 'Mentor',
}

/** Human summary, e.g. ["Campus: Bengaluru", "Status: Approved +1", "No update for 7+ days"]. */
export function describeFilters(
  f: AlertFilters,
  options?: FilterOptions | null,
  /** Student name -> display name, when the caller has them (the picker). */
  studentNames?: Map<string, string>,
  /** Unit name -> display name (for org_unit). */
  unitNames?: Map<string, string>,
): string[] {
  const statusPart = () => {
    const v = f.status ?? []
    return v.length ? [`Status: ${v[0]}${v.length > 1 ? ` +${v.length - 1}` : ''}`] : []
  }
  if (f.mode === 'students') {
    const picked = f.student ?? []
    if (!picked.length) return ['No students picked yet']
    const first = studentNames?.get(picked[0])
    const who = first
      ? `Students: ${first}${picked.length > 1 ? ` +${picked.length - 1}` : ''}`
      : `${picked.length} selected student${picked.length === 1 ? '' : 's'}`
    return [who, ...statusPart()]
  }
  const names: Partial<Record<ListKey, Map<string, string>>> = {
    campus: new Map((options?.campuses ?? []).map((c) => [c.name, c.ao_name || c.name])),
    irb_unit: new Map((options?.programmes ?? []).map((p) => [p.name, p.ao_name || p.name])),
    // Faculty names are autoincrement integers on the wire.
    faculty_mentor: new Map((options?.mentors ?? []).map((m) => [String(m.name), m.full_name || String(m.name)])),
    org_unit: unitNames,
  }
  const parts: string[] = []
  for (const k of LIST_KEYS) {
    const v = f[k]
    if (!v?.length) continue
    const first = names[k]?.get(v[0]) ?? v[0]
    parts.push(`${LABELS[k]}: ${first}${v.length > 1 ? ` +${v.length - 1}` : ''}`)
  }
  if (f.inactive_days) parts.push(`No update for ${f.inactive_days}+ days`)
  return parts.length ? parts : ['All students with a project']
}
