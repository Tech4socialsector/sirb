import { io, type Socket } from 'socket.io-client'
import { onUnmounted } from 'vue'

let socket: Socket | null = null

function getSocket(): Socket {
  if (socket) return socket
  const host = window.location.hostname
  const siteName = (window as unknown as { sitename?: string }).sitename || host
  socket = io(`${window.location.protocol}//${host}/${siteName}`, {
    withCredentials: true,
    reconnection: true,
    path: '/socket.io',
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
