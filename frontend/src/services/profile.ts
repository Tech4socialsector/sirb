import { call } from './api'

export interface StudentRecord {
  name: string
  student_id: string
  full_name: string
  academic_year: string | null
}

export interface FacultyRecord {
  name: string
  full_name: string
}

/** The signed-in user's own Student / Faculty record (sirb_api.auth.get_my_profile). */
export function fetchMyProfile() {
  return call<{ student: StudentRecord | null; faculty: FacultyRecord | null }>('sirb.sirb_api.auth.get_my_profile')
}
