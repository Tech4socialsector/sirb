import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

export function useAuth() {
  const store = useAuthStore()
  const { currentUser, loading, error, initialized } = storeToRefs(store)
  return { currentUser, loading, error, initialized, load: store.load }
}
