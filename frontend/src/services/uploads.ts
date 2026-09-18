import { ApiError } from './api'

export interface UploadedFile {
  file_url: string
  name: string
}

/**
 * Uploads a file via Frappe's standard multipart endpoint. Kept separate
 * from call() in api.ts since this is multipart/form-data, not JSON.
 */
export async function uploadFile(file: File): Promise<UploadedFile> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('is_private', '1')

  let response: Response
  try {
    response = await fetch('/api/method/upload_file', {
      method: 'POST',
      headers: {
        'X-Frappe-CSRF-Token': (window as unknown as { csrf_token?: string }).csrf_token || '',
      },
      body: formData,
    })
  } catch {
    throw new ApiError('Could not reach the server while uploading the file.', 'network')
  }

  if (!response.ok) {
    throw new ApiError('The file could not be uploaded. Please try again.', 'server', response.status)
  }

  const body = await response.json()
  return body.message as UploadedFile
}

export async function enqueueStudentUpload(args: { irb_unit: string; irb_cycle: string; file_url: string }) {
  const { call } = await import('./api')
  return call<string>('sirb.api.enque_student_upload', args)
}

export async function enqueueFacultyUpload(args: { ao_unit: string; file_url: string }) {
  const { call } = await import('./api')
  return call<string>('sirb.api.enque_faculty_upload', args)
}
