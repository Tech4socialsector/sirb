import { computed, reactive } from 'vue'
import { useRealtime } from './useRealtime'

export interface LogLine {
  timestamp: string
  message: string
  isError: boolean
}

interface ImportProgressPayload {
  progress: number
  status?: string
  error?: number
}

/**
 * Drives the progress bar + live log + completion state for the Student
 * and Faculty uploaders, subscribing to the same realtime events the
 * background import jobs already publish
 * (sirb_student_import_progress / sirb_faculty_import_progress) — one
 * message per CSV row processed, matching the existing backend behavior.
 */
export function useUploader(realtimeEvent: string) {
  const { subscribe, unsubscribe } = useRealtime()

  const state = reactive({
    submitting: false,
    active: false,
    progress: 0,
    log: [] as LogLine[],
    completed: false,
    hadError: false,
  })

  const isBusy = computed(() => state.submitting || (state.active && !state.completed))

  function reset() {
    state.active = false
    state.progress = 0
    state.log = []
    state.completed = false
    state.hadError = false
  }

  function start() {
    reset()
    state.active = true
    subscribe<ImportProgressPayload>(realtimeEvent, (data) => {
      state.progress = data.progress ?? 0
      const isError = data.error === 1
      if (isError) state.hadError = true
      if (data.status) {
        state.log.push({
          timestamp: new Date().toLocaleTimeString(),
          message: data.status,
          isError,
        })
      }
      if (state.progress >= 100) {
        state.completed = true
        unsubscribe(realtimeEvent)
      }
    })
  }

  return { state, isBusy, start, reset }
}
