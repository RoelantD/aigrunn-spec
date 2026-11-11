import { ArrowRight, History, Zap } from 'lucide-react'
import type { AgentEvent, Run } from '../api/types'
import { cx } from './ui'

/** Most recent escalation for the given part, if any (FR-035). */
export function latestEscalation(events: AgentEvent[], day: number | null, part: number | null): AgentEvent | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i]
    if (e.type === 'agent.escalation' && e.day === day && e.part === part) return e
  }
  return null
}

export function EscalationBanner({ event, large = false }: { event: AgentEvent | null; large?: boolean }) {
  if (!event) return null
  return (
    <div
      role="status"
      className={cx(
        'animate-slide-in flex items-center gap-3 rounded-xl border border-opus/50 bg-gradient-to-r from-sol/10 via-opus/15 to-opus/5 px-4',
        large ? 'py-3 text-xl' : 'py-2 text-sm',
      )}
    >
      <Zap className="shrink-0 text-opus" size={large ? 26 : 18} />
      <span className="font-semibold text-sol">{event.data.from_model}</span>
      <ArrowRight className="shrink-0 text-ink-300" size={large ? 24 : 16} />
      <span className="font-semibold text-opus">{event.data.to_model}</span>
      <span className="min-w-0 truncate text-ink-300">— {event.data.reason}</span>
    </div>
  )
}

export function ReplayBanner({ run }: { run: Run | null | undefined }) {
  if (!run || run.mode !== 'replay') return null
  return (
    <div
      role="alert"
      className="sticky top-0 z-30 flex items-center justify-center gap-2 border-b border-warn/50 bg-warn/20 px-4 py-2 text-sm font-semibold tracking-wide text-warn"
    >
      <History size={18} />
      REPLAY of recorded run #{run.source_run_id} — not live. No Advent of Code, model or sandbox calls are made.
    </div>
  )
}
