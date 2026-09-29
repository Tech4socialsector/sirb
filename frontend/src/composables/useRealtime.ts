import { initSocket, toast } from 'frappe-ui'
import type { Socket } from 'socket.io-client'
import { onUnmounted } from 'vue'

let socket: Socket | null = null
let connectionIssueShown = false

function getSocket(): Socket {
  if (socket) return socket
  // Frappe's realtime (socket.io) server runs on its own port — separate
  // from the webserver this page was served from — configured per-site
  // as `socketio_port` (see sites/common_site_config.json) and exposed to
  // the browser as a top-level `window.socketio_port` boot global. The
  // previous hand-rolled connection here ignored that entirely and
  // pointed socket.io at the page's own origin with no port at all, so it
  // never actually reached the realtime server — upload progress events
  // were being published by the backend but never received here.
  const port = (window as unknown as { socketio_port?: number }).socketio_port
  socket = initSocket(port ? { port } : {}) as Socket

  // A silent failure here previously looked identical to "nothing to
  // report yet" from the caller's point of view — surface it instead of
  // leaving the uploader/progress UI looking stuck with no explanation.
  socket.on('connect_error', () => {
    if (connectionIssueShown) return
    connectionIssueShown = true
    toast.error('Live progress updates are unavailable right now (realtime connection failed). The upload itself is still running in the background.')
  })
  socket.on('connect', () => {
    connectionIssueShown = false
  })

  return socket
}

/**
 * Thin wrapper over Frappe's realtime (socket.io) channel, mirroring
 * frappe.realtime.on/off semantics used by the legacy uploader pages.
 * Every subscription registered through this composable is automatically
 * torn down when the owning component unmounts, so a page navigating away
 * mid-upload can never leave a duplicate listener behind.
 */
export function useRealtime() {
  const activeHandlers: { event: string; handler: (...args: unknown[]) => void }[] = []

  function subscribe<T = unknown>(event: string, handler: (payload: T) => void) {
    const s = getSocket()
    const wrapped = (payload: unknown) => handler(payload as T)
    s.on(event, wrapped)
    activeHandlers.push({ event, handler: wrapped })
  }

  function unsubscribe(event: string) {
    const s = getSocket()
    const remaining: typeof activeHandlers = []
    for (const entry of activeHandlers) {
      if (entry.event === event) {
        s.off(event, entry.handler)
      } else {
        remaining.push(entry)
      }
    }
    activeHandlers.length = 0
    activeHandlers.push(...remaining)
  }

  function cleanup() {
    const s = getSocket()
    for (const entry of activeHandlers) {
      s.off(entry.event, entry.handler)
    }
    activeHandlers.length = 0
  }

  onUnmounted(cleanup)

  return { subscribe, unsubscribe, cleanup }
}
