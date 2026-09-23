import { ApiError, extractServerMessage } from './api'

export interface UploadedFile {
  file_url: string
  name: string
}

/** Where an uploaded file belongs. Attaching it to the document is what
 * lets everyone who can read that document (mentor, reviewers) open a
 * private file — otherwise only the uploader can. */
export interface AttachTarget {
  doctype: string
  docname: string
  fieldname: string
}

/**
 * Uploads a file via Frappe's standard multipart endpoint. Kept separate
 * from call() in api.ts since this is multipart/form-data, not JSON.
 */
export async function uploadFile(file: File, attachTo?: AttachTarget): Promise<UploadedFile> {
  const formData = new FormData()
  formData.append('file', file, file.name)
  formData.append('is_private', '1')
  if (attachTo) {
    formData.append('doctype', attachTo.doctype)
    formData.append('docname', attachTo.docname)
    formData.append('fieldname', attachTo.fieldname)
  }

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

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    // e.g. a proxy's HTML 413 page
  }

  if (!response.ok) {
    if (response.status === 413) {
      throw new ApiError('This file is too large to upload. Please compress it or split it into smaller files.', 'validation', 413)
    }
    // Frappe explains size/type rejections in _server_messages — show that.
    const serverMessage = extractServerMessage(body)?.replace(/<[^>]*>/g, '')
    throw new ApiError(serverMessage || 'The file could not be uploaded. Please try again.', 'server', response.status)
  }

  return (body as { message: UploadedFile }).message
}

export async function enqueueStudentUpload(args: { irb_unit: string; irb_cycle: string; file_url: string }) {
  const { call } = await import('./api')
  return call<string>('sirb.api.enque_student_upload', args)
}

export async function enqueueFacultyUpload(args: { ao_unit: string; file_url: string }) {
  const { call } = await import('./api')
  return call<string>('sirb.api.enque_faculty_upload', args)
}
