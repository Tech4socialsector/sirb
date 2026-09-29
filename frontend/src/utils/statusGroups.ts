/** Project statuses grouped by who has to act — the way the IRB office talks about them. */
export interface StatusGroup {
  key: string
  label: string
  hint: string
  statuses: string[]
}

export const STATUS_GROUPS: StatusGroup[] = [
  {
    key: 'student',
    label: 'Student action needed',
    hint: 'Proposal or corrections pending with the student',
    statuses: [
      'Awaiting proposal completion by student',
      'Awaiting student correction for mentor feedback',
      'Awaiting student correction for reviewer feedback',
    ],
  },
  { key: 'mentor', label: 'With the mentor', hint: 'Waiting for the faculty mentor', statuses: ['Awaiting Faculty mentor approval'] },
  {
    key: 'reviewers',
    label: 'With the reviewers',
    hint: 'IRB review in progress',
    statuses: [
      'Awaiting primary reviewer comments to secondary reviewer',
      'Awaiting secondary reviewer comments to primary reviewer',
      'Awaiting reviewer feedback to student',
    ],
  },
  {
    key: 'approval',
    label: 'Approval',
    hint: 'Provisional or final approval',
    statuses: ['Provisionally approved', 'Awaiting final approval', 'Approved'],
  },
]

/** The groups for the statuses that exist, plus "Other" for any status no group covers. */
export function groupsFor(statuses: string[]): StatusGroup[] {
  const known = new Set(statuses)
  const out = STATUS_GROUPS.map((g) => ({ ...g, statuses: g.statuses.filter((s) => known.has(s)) })).filter((g) => g.statuses.length)
  const grouped = new Set(out.flatMap((g) => g.statuses))
  const rest = statuses.filter((s) => !grouped.has(s))
  if (rest.length) out.push({ key: 'other', label: 'Other', hint: '', statuses: rest })
  return out
}
