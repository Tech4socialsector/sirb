// Sample CSV templates for the bulk uploaders. Column headers here must
// stay in sync with what the backend importer actually expects:
// - Faculty: sirb.api.import_faculty_list (_resolve_faculty_columns)
// - Student: sirb.api.analyze_student_headers / import_student_irb_information
// (student-name-N / student-id-N / student-email-N, 1..N, plus mentor-name /
// mentor-email — the importer is header-driven, so "group" projects are
// just more of those N columns on one row, not a different backend format.)

function downloadCsv(filename: string, rows: string[][]) {
  const content = rows.map((row) => row.map(escapeCsvCell).join(',')).join('\r\n')
  const blob = new Blob(['﻿' + content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function escapeCsvCell(value: string) {
  if (/[",\r\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

export function downloadFacultySampleSheet() {
  downloadCsv('faculty_upload_sample.csv', [
    ['Faculty name', "Faculty's email ID"],
    ['Jane Doe', 'jane.doe@example.edu'],
    ['John Smith', 'john.smith@example.edu'],
  ])
}

export function downloadStudentSampleSheet(kind: 'individual' | 'group') {
  if (kind === 'individual') {
    downloadCsv('student_upload_sample_individual.csv', [
      ['Student-name-1', 'student-id-1', 'Student-email-1', 'Mentor-name', 'Mentor-email'],
      ['Asha Rao', 'BTC2024001', 'asha.rao@example.edu', 'Dr. Vishnu Prakash', 'vishnu.prakash@example.edu'],
    ])
    return
  }
  downloadCsv('student_upload_sample_group.csv', [
    [
      'Student-name-1',
      'student-id-1',
      'Student-email-1',
      'Student-name-2',
      'student-id-2',
      'Student-email-2',
      'Mentor-name',
      'Mentor-email',
    ],
    [
      'Asha Rao',
      'BTC2024001',
      'asha.rao@example.edu',
      'Kiran Mehta',
      'BTC2024002',
      'kiran.mehta@example.edu',
      'Dr. Vishnu Prakash',
      'vishnu.prakash@example.edu',
    ],
  ])
}
