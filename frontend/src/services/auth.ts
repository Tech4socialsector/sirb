import { call } from './api'
import type { CurrentUser } from '@/types/auth'

export function fetchCurrentUser() {
  return call<CurrentUser>('sirb.sirb_api.auth.get_current_user')
}
