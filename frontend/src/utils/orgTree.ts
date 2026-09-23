import type { OrgUnit } from '@/types/setup'

export interface OrgTreeIndex {
  byName: Map<string, OrgUnit>
  children: Map<string | null, OrgUnit[]>
  depth: (name: string) => number
  /** The unit itself plus every unit beneath it. */
  subtree: (name: string) => Set<string>
  /** "Campus › School › Programme" — for disambiguating same-named units. */
  path: (name: string) => string
  /** Every unit in depth-first (tree display) order. */
  ordered: OrgUnit[]
}

/**
 * Builds lookups from the flat unit list. Walks by parent link rather than
 * trusting lft/rgt ordering, and guards against cycles so a corrupt
 * parent chain can't hang the page.
 */
export function buildOrgIndex(units: OrgUnit[]): OrgTreeIndex {
  const byName = new Map(units.map((u) => [u.name, u]))
  const children = new Map<string | null, OrgUnit[]>()
  for (const u of units) {
    // A parent that no longer exists is treated as a root so the node stays visible.
    const key = u.parent && byName.has(u.parent) ? u.parent : null
    if (!children.has(key)) children.set(key, [])
    children.get(key)!.push(u)
  }
  // Same sibling order as the Desk tree view (nested-set position).
  for (const list of children.values()) list.sort((a, b) => (a.lft ?? 0) - (b.lft ?? 0) || a.ao_name.localeCompare(b.ao_name))

  function ancestors(name: string): OrgUnit[] {
    const out: OrgUnit[] = []
    const seen = new Set<string>([name])
    let cur = byName.get(name)?.parent
    while (cur && byName.has(cur) && !seen.has(cur)) {
      seen.add(cur)
      out.unshift(byName.get(cur)!)
      cur = byName.get(cur)!.parent
    }
    return out
  }

  function subtree(name: string) {
    const out = new Set<string>()
    const stack = [name]
    while (stack.length) {
      const n = stack.pop()!
      if (out.has(n)) continue
      out.add(n)
      for (const c of children.get(n) || []) stack.push(c.name)
    }
    return out
  }

  const ordered: OrgUnit[] = []
  const visited = new Set<string>()
  function walk(parent: string | null) {
    for (const u of children.get(parent) || []) {
      if (visited.has(u.name)) continue
      visited.add(u.name)
      ordered.push(u)
      walk(u.name)
    }
  }
  walk(null)

  return {
    byName,
    children,
    depth: (name) => ancestors(name).length,
    subtree,
    path: (name) => [...ancestors(name), byName.get(name)].filter(Boolean).map((u) => u!.ao_name).join(' › '),
    ordered,
  }
}
