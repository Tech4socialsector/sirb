export class ApiError extends Error {
  kind: 'permission' | 'not_found' | 'validation' | 'session_expired' | 'network' | 'server'
  httpStatus?: number

  constructor(
    message: string,
    kind: ApiError['kind'],
    httpStatus?: number,
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.httpStatus = httpStatus
  }
}

function friendlyMessage(status: number, serverMessage?: string): { message: string; kind: ApiError['kind'] } {
  if (status === 401) {
    return { message: 'Your session has expired. Please log in again.', kind: 'session_expired' }
  }
  if (status === 403) {
    return { message: serverMessage || 'You do not have permission to view this.', kind: 'permission' }
  }
  if (status === 404) {
    return { message: serverMessage || 'The requested item could not be found.', kind: 'not_found' }
  }
  if (status === 417 || status === 400) {
    return { message: serverMessage || 'Please correct the highlighted errors and try again.', kind: 'validation' }
  }
  return { message: serverMessage || 'Something went wrong. Please try again.', kind: 'server' }
}

/**
 * Frappe's error envelope varies by failure path:
 * - frappe.throw(...) sets `_server_messages` (a JSON-encoded array of
 *   JSON-encoded {message, title, indicator} objects) — the richest,
 *   most user-facing source, so it takes priority.
 * - Framework-level failures (e.g. AuthenticationError from a bad
 *   login) set a plain top-level `message` string that is already
 *   human-readable.
 * - `exception` is a dotted exception class path (e.g.
 *   "frappe.exceptions.AuthenticationError") with no message text of
 *   its own — never shown directly to the user.
 */
export function extractServerMessage(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined
  const b = body as Record<string, unknown>

  if (typeof b._server_messages === 'string') {
    try {
      const parsed = JSON.parse(b._server_messages) as string[]
      const first = parsed[0]
      if (first) {
        const inner = JSON.parse(first) as { message?: string }
        if (inner.message) return inner.message
      }
    } catch {
      // fall through
    }
  }
  if (typeof b.message === 'string') return b.message
  return undefined
}

/**
 * Thin wrapper around Frappe's whitelisted-method call convention. Every
 * SIRB service function goes through this — no component ever calls
 * fetch()/frappe.call() directly (see the "API Architecture" guidance:
 * Component -> Composable -> Service -> Frappe API).
 */
export async function call<T = unknown>(method: string, args: Record<string, unknown> = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/method/${method}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': (window as unknown as { csrf_token?: string }).csrf_token || '',
      },
      body: JSON.stringify(args),
    })
  } catch {
    throw new ApiError('Could not reach the server. Check your connection and try again.', 'network')
  }

  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    // non-JSON error page (e.g. a raw traceback page) — leave body null
  }

  if (!response.ok) {
    const serverMessage = extractServerMessage(body)
    const { message, kind } = friendlyMessage(response.status, serverMessage)
    throw new ApiError(message, kind, response.status)
  }

  return (body as { message: T })?.message as T
}
