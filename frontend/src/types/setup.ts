export type AoType = 'University' | 'Campus' | 'School' | 'Department' | 'Programme'

export interface OrgUnit {
  name: string
  ao_name: string
  ao_type: AoType
  ao_code: string
  is_group: 0 | 1
  parent: string | null
  lft: number
}

export interface IrbUnitRow {
  name: string
  ao_unit: string
  ao_name: string
  mentor_required: 0 | 1
  num_reviewers: '1' | '2'
  /** Faculty Academic Organizational Unit names, in committee order. */
  members: string[]
  project_count: number
  modified: string
}

export interface FacultyMembership {
  name: string
  faculty_member: string
  ao_unit: string
  status: 'active' | 'inactive'
  faculty_name: string | null
  faculty_email: string | null
  unit_name: string | null
}

export interface FacultyRow {
  name: string
  full_name: string | null
  system_user: string | null
}

export interface SetupData {
  units: OrgUnit[]
  irb_units: IrbUnitRow[]
  memberships: FacultyMembership[]
  faculty: FacultyRow[]
  ao_types: AoType[]
}

export interface OrgUnitInput {
  name?: string
  ao_name: string
  ao_type: AoType
  ao_code?: string
  parent?: string
  is_group: boolean
  allow_root?: boolean
}

export interface IrbUnitInput {
  name?: string
  ao_unit: string
  mentor_required: boolean
  num_reviewers: '1' | '2'
  /** A person to seat on the committee, plus their existing membership row if known. */
  members: { faculty: string; membership?: string }[]
}
