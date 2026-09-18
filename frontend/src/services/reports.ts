import { call } from './api'

export function fetchProjectsByIrbUnit(args: { irb_unit?: string; status?: string; campus?: string }) {
  return call('sirb.sirb_api.anchor_reports.get_projects_by_irb_unit', args)
}

export function fetchProjectSummaryByIrbUnit(irb_unit?: string) {
  return call('sirb.sirb_api.anchor_reports.get_project_summary_by_irb_unit', { irb_unit })
}
