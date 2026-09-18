import { ref } from 'vue'
import {
  fetchFieldChangesSinceStatus,
  fetchProjectDetail,
  fetchStatusChangeHistory,
  setProjectStatus,
} from '@/services/projects'
import { ApiError } from '@/services/api'
import type { FieldChangeEntry, ProjectDetailPayload, StatusChangeEntry } from '@/types/project'

export function useProject(projectName: string) {
  const detail = ref<ProjectDetailPayload | null>(null)
  const history = ref<StatusChangeEntry[]>([])
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  const transitioning = ref(false)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const [detailResult, historyResult] = await Promise.all([
        fetchProjectDetail(projectName),
        fetchStatusChangeHistory(projectName).catch(() => [] as StatusChangeEntry[]),
      ])
      detail.value = detailResult
      history.value = historyResult
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError('Failed to load project.', 'server')
    } finally {
      loading.value = false
    }
  }

  async function fieldChangesSince(status: string): Promise<Record<string, FieldChangeEntry[]>> {
    try {
      return await fetchFieldChangesSinceStatus(projectName, status)
    } catch {
      return {}
    }
  }

  async function transitionTo(status: string) {
    transitioning.value = true
    try {
      await setProjectStatus(projectName, status)
      await load()
    } finally {
      transitioning.value = false
    }
  }

  return { detail, history, loading, error, transitioning, load, transitionTo, fieldChangesSince }
}
