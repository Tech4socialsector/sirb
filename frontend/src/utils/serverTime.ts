/**
 * Frappe sends datetimes as naive "YYYY-MM-DD HH:MM:SS[.ffffff]" strings in
 * the *server's* timezone. `new Date(str)` would read them as browser-local
 * time (wrong whenever the admin's browser is in another zone) and Safari
 * can't parse the space-separated form at all — so these helpers work on the
 * wall-clock parts directly and the UI labels the server timezone instead.
 */

const PATTERN = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/

interface Parts {
  y: number
  mo: number
  d: number
  h: number
  mi: number
}

function parse(value: string | null | undefined): Parts | null {
  const m = value ? PATTERN.exec(value) : null
  if (!m) return null
  return { y: +m[1], mo: +m[2], d: +m[3], h: +(m[4] ?? 0), mi: +(m[5] ?? 0) }
}

// Only used to *format* the parts; the Date's own timezone never matters
// because we read back exactly the fields we put in.
function asLocalDate(p: Parts) {
  return new Date(p.y, p.mo - 1, p.d, p.h, p.mi)
}

export function formatServerDateTime(value: string | null | undefined, fallback = '—') {
  const p = parse(value)
  if (!p) return fallback
  return asLocalDate(p).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatServerDate(value: string | null | undefined, fallback = '—') {
  const p = parse(value)
  if (!p) return fallback
  return asLocalDate(p).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

/** "YYYY-MM-DD HH:MM:SS" → "YYYY-MM-DDTHH:MM" for <input type="datetime-local">. */
export function toDateTimeInput(value: string | null | undefined) {
  const p = parse(value)
  if (!p) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${p.y}-${pad(p.mo)}-${pad(p.d)}T${pad(p.h)}:${pad(p.mi)}`
}

/**
 * A clock that tracks the server's wall time: the server's "now" at page
 * load plus the time elapsed in the browser since then.
 */
export function serverClock(serverNow: string) {
  const p = parse(serverNow)
  const base = p ? Date.UTC(p.y, p.mo - 1, p.d, p.h, p.mi) : Date.now()
  const loadedAt = Date.now()
  return {
    /** Server wall time shifted by `addMinutes`, as a datetime-local value. */
    input(addMinutes = 0) {
      const t = new Date(base + (Date.now() - loadedAt) + addMinutes * 60_000)
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}T${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}`
    },
    /** Next whole hour (at least 5 minutes away) as a datetime-local value. */
    nextHourInput() {
      const now = base + (Date.now() - loadedAt) + 5 * 60_000
      const t = new Date(Math.ceil(now / 3_600_000) * 3_600_000)
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}T${pad(t.getUTCHours())}:00`
    },
  }
}

/** Whole days from `value` to `now` (both server wall-clock strings); null if unparseable. */
export function daysBetween(value: string | null | undefined, now: string | null | undefined): number | null {
  const a = parse(value)
  const b = parse(now)
  if (!a || !b) return null
  const day = (p: Parts) => Date.UTC(p.y, p.mo - 1, p.d) / 86_400_000
  return Math.round(day(b) - day(a))
}

/** "today" / "yesterday" / "5 days ago" / "in 3 days". */
export function relativeDays(days: number | null): string {
  if (days === null) return ''
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days === -1) return 'tomorrow'
  return days > 0 ? `${days} days ago` : `in ${-days} days`
}
