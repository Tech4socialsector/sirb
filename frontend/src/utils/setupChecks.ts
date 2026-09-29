import type { OrgTreeIndex } from './orgTree'
import type { FacultyMembership, IrbUnitRow, SetupData } from '@/types/setup'

export type SetupTab = 'organization' | 'irb-units'

export interface SetupIssue {
  level: 'danger' | 'warning' | 'info'
  title: string
  detail: string
  tab: SetupTab
}

/**
 * Mirrors the assignment rules in sirb.utils.get_reviewers(): the primary
 * reviewer is the least-loaded committee member other than the project's
 * mentor, and the secondary (when 2 reviewers are configured) must differ
 * from both. Membership status is NOT consulted there, so inactive members
 * still get assigned — worth flagging.
 */
type CommitteeMember = Pick<FacultyMembership, 'faculty_member' | 'faculty_name' | 'status'>

export function committeeWarning(unit: {
  members: CommitteeMember[]
  num_reviewers: '1' | '2'
  mentor_required: boolean
}): { level: 'danger' | 'warning'; message: string } | null {
  const needed = Number(unit.num_reviewers) || 1
  // Count people, not rows: the same faculty listed twice is still one reviewer.
  const count = new Set(unit.members.map((m) => String(m.faculty_member))).size
  if (count < needed) {
    return {
      level: 'danger',
      message:
        count === 0
          ? `No committee members — projects in this unit won't get ${needed === 2 ? 'reviewers' : 'a reviewer'}.`
          : `Needs at least ${needed} committee members to assign ${needed} reviewers; has ${count}.`,
    }
  }
  if (unit.mentor_required && count === needed) {
    return {
      level: 'warning',
      message: `A mentor on this committee can't review their own project, so that project would be short a reviewer. Add at least ${needed + 1} members to be safe.`,
    }
  }
  const inactive = unit.members.filter((m) => m.status === 'inactive')
  if (inactive.length) {
    return {
      level: 'warning',
      message: `${inactive.map((m) => m.faculty_name || m.faculty_member).join(', ')} ${inactive.length === 1 ? 'is' : 'are'} inactive but will still be assigned reviews. Remove them from the committee if that's not intended.`,
    }
  }
  return null
}

/** Committee members as distinct people (a person listed twice appears once). */
export function resolveMembers(unit: IrbUnitRow, byName: Map<string, FacultyMembership>) {
  const seen = new Set<string>()
  const out: FacultyMembership[] = []
  for (const n of unit.members) {
    const m = byName.get(n)
    if (!m || seen.has(String(m.faculty_member))) continue
    seen.add(String(m.faculty_member))
    out.push(m)
  }
  return out
}

/** How many committee rows repeat a person already listed. */
export function duplicateMemberCount(unit: IrbUnitRow, byName: Map<string, FacultyMembership>) {
  const known = unit.members.filter((n) => byName.has(n)).length
  return known - resolveMembers(unit, byName).length
}

function listNames(names: string[], max = 3) {
  const head = names.slice(0, max).join(', ')
  return names.length > max ? `${head} and ${names.length - max} more` : head
}

export function setupIssues(data: SetupData, index: OrgTreeIndex): SetupIssue[] {
  const issues: SetupIssue[] = []

  if (!data.units.length) {
    issues.push({
      level: 'danger',
      title: 'No organisation structure yet',
      detail: 'Add your university, campuses, schools and programmes first — everything else hangs off them.',
      tab: 'organization',
    })
    return issues
  }

  if (!data.irb_units.length) {
    issues.push({
      level: 'danger',
      title: 'No IRB Units yet',
      detail: 'Students can only be uploaded into an IRB Unit. Create one for each programme that runs IRB reviews.',
      tab: 'irb-units',
    })
  }

  const byName = new Map(data.memberships.map((m) => [m.name, m]))
  for (const unit of data.irb_units) {
    const w = committeeWarning({
      members: resolveMembers(unit, byName),
      num_reviewers: unit.num_reviewers,
      mentor_required: !!unit.mentor_required,
    })
    if (w) issues.push({ level: w.level, title: unit.ao_name || unit.ao_unit, detail: w.message, tab: 'irb-units' })
    const dupes = duplicateMemberCount(unit, byName)
    if (dupes)
      issues.push({
        level: 'warning',
        title: `${unit.ao_name || unit.ao_unit}: duplicate committee ${dupes === 1 ? 'entry' : 'entries'}`,
        detail: 'The same faculty member is listed more than once. Open the IRB Unit and save it to remove the duplicate.',
        tab: 'irb-units',
      })
  }

  const onCommittee = new Set(data.irb_units.flatMap((u) => u.members))
  const noUser = data.memberships.filter((m) => onCommittee.has(m.name) && !m.faculty_email)
  if (noUser.length) {
    issues.push({
      level: 'warning',
      title: `${noUser.length} committee ${noUser.length === 1 ? 'member has' : 'members have'} no user account`,
      detail: `${listNames(noUser.map((m) => m.faculty_name || m.faculty_member))} can't log in to review until their Faculty record is linked to a User.`,
      tab: 'irb-units',
    })
  }

  const covered = new Set(data.irb_units.map((u) => u.ao_unit))
  const uncovered = data.units.filter((u) => u.ao_type === 'Programme' && !covered.has(u.name))
  if (uncovered.length) {
    issues.push({
      level: 'info',
      title: `${uncovered.length} ${uncovered.length === 1 ? 'programme has' : 'programmes have'} no IRB Unit`,
      detail: `${listNames(uncovered.map((u) => index.path(u.name)))}. Only needed if these programmes run IRB reviews.`,
      tab: 'irb-units',
    })
  }

  return issues
}
