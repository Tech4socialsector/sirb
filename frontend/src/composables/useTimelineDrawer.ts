import { reactive, readonly } from 'vue'
import type { StatusChangeEntry } from '@/types/project'

/**
 * Singleton drawer context so the Timeline button in the global TopHeader
 * can open a drawer for whatever project the current page is showing,
 * without TopHeader needing to know about project-specific state itself.
 * ProjectDetails.vue (and any future project-scoped page) calls
 * setContext() whenever its own already-loaded project/history data
 * changes (no separate fetch here — this composable is presentational
 * state only) and clearContext() on unmount; TopHeader only reads
 * `state.projectName` to decide whether to render the button at all.
 */
interface TimelineContext {
  projectName: string | null
  projectTitle: string | null
  studentName: string | null
  currentStatus: string | null
  history: StatusChangeEntry[]
  loading: boolean
}

const state = reactive<TimelineContext & { isOpen: boolean }>({
  isOpen: false,
  projectName: null,
  projectTitle: null,
  studentName: null,
  currentStatus: null,
  history: [],
  loading: false,
})

function setContext(ctx: Partial<TimelineContext>) {
  Object.assign(state, ctx)
}

function clearContext() {
  state.projectName = null
  state.projectTitle = null
  state.studentName = null
  state.currentStatus = null
  state.history = []
  state.loading = false
  state.isOpen = false
}

function open() {
  if (state.projectName) state.isOpen = true
}

function close() {
  state.isOpen = false
}

export function useTimelineDrawer() {
  return { state: readonly(state), setContext, clearContext, open, close }
}
