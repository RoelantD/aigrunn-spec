import type { UiState } from '../api/types'

export function fmtDuration(seconds: number): string {
  const s = Math.floor(seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

export function fmtUsd(n: number): string {
  return `$${(n ?? 0).toFixed(2)}`
}

export function fmtTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}

export const UI_STATE_LABEL: Record<UiState, string> = {
  unsolved: 'Unsolved',
  solving: 'Solving',
  tests_passed: 'Tests passed',
  submitted: 'Submitted',
  verified: 'Verified by Advent of Code',
  previously_completed: 'Previously completed',
  failed: 'Failed',
  blocked: 'Blocked',
  skipped: 'Skipped',
}

/** A star is shown ONLY for server-confirmed states (Constitution I). */
export function hasStar(s: UiState): boolean {
  return s === 'verified' || s === 'previously_completed'
}

export function modelName(key: string | null | undefined, names: { workhorse: string; escalation: string }): string {
  if (key === 'workhorse') return names.workhorse
  if (key === 'escalation') return names.escalation
  return '—'
}
