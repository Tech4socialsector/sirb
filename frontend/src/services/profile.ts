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

export function fetchStudentRecord(name: string) {
  return call<StudentRecord>('frappe.client.get', { doctype: 'Student', name })
}

export function fetchFacultyRecord(name: string) {
  return call<FacultyRecord>('frappe.client.get', { doctype: 'Faculty', name })
}
