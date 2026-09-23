import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '@/services/api'
import type { ProjectListRow } from '@/types/project'
import type { WorklistBucket } from '@/services/projects'

const BUCKETS: WorklistBucket[] = ['pending', 'unapproved', 'approved']

/**
 * Loads all three worklist buckets (pending/in-progress/approved) once, in
 * parallel, instead of re-fetching every time the active tab changes —
 * this is what makes it possible to show a real count on every tab
 * up front, and switching tabs afterwards is instant/local.
 */
export function useProjects(fetcher: (bucket: WorklistBucket) => Promise<ProjectListRow[]>) {
  const buckets = reactive<Record<WorklistBucket, ProjectListRow[]>>({
    pending: [],
    unapproved: [],
    approved: [],
  })
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  // The active tab lives in `?tab=` so dashboard cards can deep-link to a
  // tab, and Back/Forward and reloads keep it.
  const route = useRoute()
  const router = useRouter()
  const tabFromQuery = (): WorklistBucket => {
    const t = route.query.tab
    return typeof t === 'string' && (BUCKETS as string[]).includes(t) ? (t as WorklistBucket) : 'pending'
  }
  const bucket = ref<WorklistBucket>(tabFromQuery())
  watch(() => route.query.tab, () => (bucket.value = tabFromQuery()))
  watch(bucket, (b) => {
    if (tabFromQuery() === b) return
    const query = { ...route.query }
    if (b === 'pending') delete query.tab
    else query.tab = b
    router.replace({ query })
  })

  const rows = computed(() => buckets[bucket.value])
  const counts = computed(() => ({
    pending: buckets.pending.length,
    unapproved: buckets.unapproved.length,
    approved: buckets.approved.length,
  }))

  async function load() {
    loading.value = true
    error.value = null
    try {
      const results = await Promise.all(BUCKETS.map((b) => fetcher(b)))
      BUCKETS.forEach((b, i) => (buckets[b] = results[i]))
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError('Failed to load projects.', 'server')
    } finally {
      loading.value = false
    }
  }

  return { rows, loading, error, bucket, counts, load }
}
