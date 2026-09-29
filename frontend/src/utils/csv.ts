export type CsvValue = string | number | null | undefined

// Titles, names etc. are user-entered; a cell starting with one of these is
// run as a formula by Excel/Sheets, so it's prefixed with a quote.
const FORMULA_PREFIX = /^[=+\-@\t\r]/

function escapeCell(value: CsvValue): string {
  let s = String(value ?? '')
  if (typeof value === 'string' && FORMULA_PREFIX.test(s)) s = `'${s}`
  return `"${s.replace(/"/g, '""')}"`
}

export function toCsv(header: string[], rows: CsvValue[][]): string {
  return [header, ...rows].map((row) => row.map(escapeCell).join(',')).join('\r\n')
}

/** Filename-safe local date, e.g. 2026-09-23. */
export function csvDateStamp(d = new Date()) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function downloadCsv(filename: string, header: string[], rows: CsvValue[][]) {
  // BOM so Excel reads the file as UTF-8 (non-ASCII names stay intact).
  const blob = new Blob(['﻿' + toCsv(header, rows)], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Revoking synchronously can cancel the download in some browsers.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
