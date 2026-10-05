import { call } from './api'

const NS = 'sirb.sirb_api.programme_access'

/** Read only: IRB Programme Viewer. Read & Write: IRB Programme Manager. */
export type AccessLevel = 'Read only' | 'Read & Write'

export interface ProgrammeAccessRecord {
  user: string
  full_name: string | null
  enabled: 0 | 1
  access_level: AccessLevel
  /** 0 if the role for this access level was removed from the user elsewhere. */
  has_role: 0 | 1
  modified: string
  programmes: { irb_unit: string; programme_name: string }[]
}

export interface ProgrammeOption {
  name: string
  ao_name: string
  project_count: number
}

export interface ProgrammeAccessData {
  records: ProgrammeAccessRecord[]
  programmes: ProgrammeOption[]
}

export function fetchProgrammeAccess() {
  return call<ProgrammeAccessData>(`${NS}.get_programme_access`)
}

export function saveProgrammeAccess(user: string, programmes: string[], isNew: boolean, accessLevel: AccessLevel) {
  return call<string>(`${NS}.save_programme_access`, {
    user,
    programmes,
    is_new: isNew ? 1 : 0,
    access_level: accessLevel,
  })
}

export function deleteProgrammeAccess(user: string) {
  return call<void>(`${NS}.delete_programme_access`, { user })
}
