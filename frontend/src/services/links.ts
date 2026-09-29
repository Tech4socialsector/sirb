import { call } from './api'

export interface LinkOption {
  value: string
  label: string
  description?: string
}

export async function searchLink(doctype: string, txt: string): Promise<LinkOption[]> {
  const results = await call<{ value: string; label?: string; description?: string }[]>(
    'frappe.desk.search.search_link',
    { doctype, txt: txt || '' },
  )
  return results.map((r) => ({ value: r.value, label: r.label || r.value, description: r.description }))
}
