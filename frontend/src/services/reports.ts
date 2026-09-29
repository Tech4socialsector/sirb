import { call } from './api'
import type { ProjectReportRow } from '@/types/reports'

export function fetchProjectsByIrbUnit(args: { irb_unit?: string; status?: string; campus?: string } = {}) {
  return call<ProjectReportRow[]>('sirb.sirb_api.anchor_reports.get_projects_by_irb_unit', args)
}

