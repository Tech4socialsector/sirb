export interface FrappeCallOptions {
  method: string
  args?: Record<string, unknown>
}

export interface FrappeListResponse<T> {
  message: T
}

export interface ApiErrorPayload {
  message?: string
  exc_type?: string
  _server_messages?: string
}
