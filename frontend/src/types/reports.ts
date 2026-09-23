// Row/response shapes for sirb.sirb_api.anchor_reports — the existing
// Anchor-facing report APIs (ported from the "Projects by IRB Unit" /
// "Project Summary by IRB Unit" Script Reports). This page derives every
// KPI/chart/table from these two calls; it never re-implements their SQL.

export interface ReportStudent {
  name: string
  email: string
}

export interface ProjectReportRow {
  irb_unit: string
  project_status: string
  project_title: string
  irb_cycle: string | null
  last_updated: string
  days_in_state: number
  student_info: string[]
  students: ReportStudent[]
  mentor: string | null
  mentor_name: string | null
  mentor_email: string | null
  primary_reviewer: string | null
  primary_reviewer_name: string | null
  primary_reviewer_email: string | null
  secondary_reviewer: string | null
  secondary_reviewer_name: string | null
  secondary_reviewer_email: string | null
  project_name: string
}

export interface ProgrammeSummaryRow {
  irb_unit: string
  project_status: string
  project_count: number
}

export interface ProjectSummaryResponse {
  rows: ProgrammeSummaryRow[]
  chart: {
    type: string
    data: { labels: string[]; datasets: { values: number[] }[] }
  }
}
