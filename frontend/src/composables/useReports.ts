import { computed, ref, type Ref } from 'vue'
import { fetchProjectsByIrbUnit } from '@/services/reports'
import { ApiError } from '@/services/api'
import type { ProjectReportRow } from '@/types/reports'

// Mirrors IRB Project's real `status` Select options (see types/project.ts
// PROJECT_STATUSES, the same canonical list) to a short bucket key —
// presentational grouping of an already-real enum, not a re-derivation of
// business logic. Kept local because the admin-only STATUS_KEY_MAP in
// irb_admin_console.py isn't reachable by the Anchor role this page serves.
const STATUS_BUCKET: Record<string, string> = {
  'Awaiting proposal completion by student': 'student_action',
  'Awaiting Faculty mentor approval': 'mentor_review',
  'Awaiting student correction for mentor feedback': 'student_action',
  'Awaiting primary reviewer comments to secondary reviewer': 'primary_review',
  'Awaiting secondary reviewer comments to primary reviewer': 'secondary_review',
  'Awaiting reviewer feedback to student': 'primary_review',
  'Awaiting student correction for reviewer feedback': 'student_action',
  'Provisionally approved': 'final_approval',
  'Awaiting final approval': 'final_approval',
  Approved: 'approved',
}
export { STATUS_BUCKET }
export const BUCKET_LABELS: Record<string, string> = {
  student_action: 'Student Action',
  mentor_review: 'Mentor Review',
  primary_review: 'Primary Review',
  secondary_review: 'Secondary Review',
  final_approval: 'Final Approval',
  approved: 'Approved',
}
export const BUCKET_ORDER = ['student_action', 'mentor_review', 'primary_review', 'secondary_review', 'final_approval', 'approved']

export interface AgingRow extends ProjectReportRow {
  bucket: '0-2' | '3-5' | '6-10' | '10+'
}

export interface ReportFilters {
  programmes: string[]
  statuses: string[]
  cycles: string[]
  search: string
}

export function useReports(filters: Ref<ReportFilters>) {
  const allRows = ref<ProjectReportRow[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  const lastRefreshed = ref<Date | null>(null)

  // One unfiltered fetch per refresh; every filter is applied client-side
  // below. The server's `irb_unit` parameter expects the IRB Unit doc name
  // while rows carry the programme's display name, so filtering server-side
  // by the dropdown value silently matched nothing — and it only takes one
  // value, which multi-select can't use anyway.
  async function refresh() {
    loading.value = true
    error.value = null
    try {
      allRows.value = await fetchProjectsByIrbUnit()
      lastRefreshed.value = new Date()
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError('Failed to load reports.', 'server')
    } finally {
      loading.value = false
    }
  }

  const programmeOptions = computed(() => [...new Set(allRows.value.map((r) => r.irb_unit))].filter(Boolean).sort())
  const statusOptions = computed(() => [...new Set(allRows.value.map((r) => r.project_status))].filter(Boolean).sort())
  const cycleOptions = computed(() => [...new Set(allRows.value.map((r) => r.irb_cycle))].filter(Boolean).sort() as string[])

  // Every KPI, chart, table and drill-down reads this, so they always agree
  // with each other and with the filter bar. An empty selection = "all".
  const detailRows = computed(() => {
    const { programmes, statuses, cycles, search } = filters.value
    let rows = allRows.value
    if (programmes.length) rows = rows.filter((r) => programmes.includes(r.irb_unit))
    if (statuses.length) rows = rows.filter((r) => statuses.includes(r.project_status))
    if (cycles.length) rows = rows.filter((r) => !!r.irb_cycle && cycles.includes(r.irb_cycle))
    const term = search.trim().toLowerCase()
    if (term) {
      rows = rows.filter((r) =>
        [r.project_title, r.irb_unit, r.mentor_name, r.primary_reviewer_name, r.secondary_reviewer_name, String(r.project_name), ...r.students.map((s) => s.name)]
          .filter(Boolean)
          .some((v) => v!.toLowerCase().includes(term)),
      )
    }
    return rows
  })

  const bucketCounts = computed(() => {
    const counts: Record<string, number> = Object.fromEntries(BUCKET_ORDER.map((k) => [k, 0]))
    for (const row of detailRows.value) {
      const bucket = STATUS_BUCKET[row.project_status]
      if (bucket) counts[bucket] += 1
    }
    return counts
  })

  const totalProjects = computed(() => detailRows.value.length)

  // One row per programme with a count per workflow stage. Built from the
  // project rows (one per project) rather than the summary report, which
  // counts Student Project Mapping rows and so counted a group project
  // once per student.
  const programmeMatrix = computed(() => {
    const byProgramme = new Map<string, Record<string, number>>()
    for (const r of detailRows.value) {
      const bucket = STATUS_BUCKET[r.project_status]
      if (!bucket) continue
      const programme = r.irb_unit || 'Unassigned'
      if (!byProgramme.has(programme)) byProgramme.set(programme, Object.fromEntries(BUCKET_ORDER.map((k) => [k, 0])))
      byProgramme.get(programme)![bucket] += 1
    }
    return [...byProgramme.entries()]
      .map(([programme, buckets]) => ({
        programme,
        total: Object.values(buckets).reduce((a, b) => a + b, 0),
        ...buckets,
      }))
      .sort((a, b) => a.programme.localeCompare(b.programme))
  })

  function agingBucket(days: number): AgingRow['bucket'] {
    if (days <= 2) return '0-2'
    if (days <= 5) return '3-5'
    if (days <= 10) return '6-10'
    return '10+'
  }
  const agingRows = computed<AgingRow[]>(() =>
    detailRows.value
      .filter((r) => r.project_status !== 'Approved')
      .map((r) => ({ ...r, bucket: agingBucket(r.days_in_state) })),
  )
  const agingCounts = computed(() => {
    const counts: Record<AgingRow['bucket'], number> = { '0-2': 0, '3-5': 0, '6-10': 0, '10+': 0 }
    for (const r of agingRows.value) counts[r.bucket] += 1
    return counts
  })

  // Per-person workload, derived entirely from the already-fetched detail
  // rows (each row already carries its mentor/primary/secondary name) —
  // no separate per-reviewer request.
  type WorkloadRole = 'mentor' | 'primary_reviewer' | 'secondary_reviewer'
  const ROLE_PENDING_BUCKET: Record<WorkloadRole, string> = {
    mentor: 'mentor_review',
    primary_reviewer: 'primary_review',
    secondary_reviewer: 'secondary_review',
  }
  const ROLE_NAME_FIELD: Record<WorkloadRole, 'mentor_name' | 'primary_reviewer_name' | 'secondary_reviewer_name'> = {
    mentor: 'mentor_name',
    primary_reviewer: 'primary_reviewer_name',
    secondary_reviewer: 'secondary_reviewer_name',
  }

  function workloadFor(role: WorkloadRole) {
    const nameField = ROLE_NAME_FIELD[role]
    const pendingBucket = ROLE_PENDING_BUCKET[role]
    const byPerson = new Map<string, { name: string; assigned: number; pending: number; completed: number; returned: number }>()
    for (const row of detailRows.value) {
      const name = row[nameField]
      if (!name) continue
      if (!byPerson.has(name)) byPerson.set(name, { name, assigned: 0, pending: 0, completed: 0, returned: 0 })
      const entry = byPerson.get(name)!
      entry.assigned += 1
      const bucket = STATUS_BUCKET[row.project_status]
      if (bucket === pendingBucket) entry.pending += 1
      if (bucket === 'approved') entry.completed += 1
      if (row.project_status.includes('correction')) entry.returned += 1
    }
    return [...byPerson.values()].sort((a, b) => b.pending - a.pending)
  }

  const mentorWorkload = computed(() => workloadFor('mentor'))
  const primaryReviewerWorkload = computed(() => workloadFor('primary_reviewer'))
  const secondaryReviewerWorkload = computed(() => workloadFor('secondary_reviewer'))

  return {
    allRows,
    detailRows,
    loading,
    error,
    lastRefreshed,
    refresh,
    programmeOptions,
    statusOptions,
    cycleOptions,
    bucketCounts,
    totalProjects,
    programmeMatrix,
    agingRows,
    agingCounts,
    mentorWorkload,
    primaryReviewerWorkload,
    secondaryReviewerWorkload,
  }
}
