import { call } from './api'
import type { IrbUnitInput, OrgUnitInput, SetupData } from '@/types/setup'

const NS = 'sirb.sirb_api.setup'

export function fetchSetupData() {
  return call<SetupData>(`${NS}.get_setup_data`)
}

export function saveOrgUnit(data: OrgUnitInput) {
  return call<string>(`${NS}.save_org_unit`, { data })
}

export function deleteOrgUnit(name: string) {
  return call<void>(`${NS}.delete_org_unit`, { name })
}

export function saveIrbUnit(data: IrbUnitInput) {
  return call<string>(`${NS}.save_irb_unit`, { data })
}

export function deleteIrbUnit(name: string) {
  return call<void>(`${NS}.delete_irb_unit`, { name })
}
