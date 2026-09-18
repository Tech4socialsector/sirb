import { ref } from 'vue'
import { ApiError } from '@/services/api'
import type { ProjectListRow } from '@/types/project'
import type { WorklistBucket } from '@/services/projects'

export function useProjects(fetcher: (bucket: WorklistBucket) => Promise<ProjectListRow[]>) {
  const rows = ref<ProjectListRow[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  const bucket = ref<WorklistBucket>('pending')

  async function load(newBucket?: WorklistBucket) {
    if (newBucket) bucket.value = newBucket
    loading.value = true
    error.value = null
    try {
      rows.value = await fetcher(bucket.value)
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError('Failed to load projects.', 'server')
    } finally {
      loading.value = false
    }
  }

  return { rows, loading, error, bucket, load }
}
