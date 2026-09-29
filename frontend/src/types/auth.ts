export type SirbRole =
  | 'Student'
  | 'Faculty Member'
  | 'Faculty Mentor'
  | 'Primary IRB Reviewer'
  | 'Secondary IRB Reviewer'
  | 'IRB Reviewer'
  | 'Anchor'
  | 'System Manager'
  | 'Administrator'

export interface CurrentUser {
  user: string
  full_name: string
  roles: string[]
  is_student: boolean
  is_faculty: boolean
  student_id: string | null
  faculty_id: string | null
}
