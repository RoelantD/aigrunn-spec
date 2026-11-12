import { Ban, CircleDashed, CircleSlash, Hourglass, Loader2, Send, Star, TestTube2, XCircle } from 'lucide-react'
import type { AgentEvent, DayInfo, PartInfo, UiState } from '../api/types'
import { UI_STATE_LABEL, hasStar } from '../lib/format'
import { cx } from './ui'

const STATE_STYLE: Record<UiState, string> = {
  unsolved: 'border-ink-700 bg-ink-800/60 text-ink-400',
  solving: 'border-sol/70 bg-sol/10 text-sol animate-pulse-ring',
  tests_passed: 'border-ok/50 bg-ok/10 text-ok',
  submitted: 'border-warn/60 bg-warn/10 text-warn',
  verified: 'border-star/70 bg-star/15 text-star',
  previously_completed: 'border-star/30 bg-star/5 text-star/70',
  failed: 'border-bad/60 bg-bad/10 text-bad',
  blocked: 'border-ink-600 bg-ink-800 text-ink-400',
  skipped: 'border-ink-600 bg-ink-800 text-ink-400',
}

function PartIcon({ s, size }: { s: UiState; size: number }) {
  switch (s) {
    case 'verified':
    case 'previously_completed':
      return <Star size={size} fill="currentColor" strokeWidth={1.5} />
    case 'solving':
      return <Loader2 size={size} className="animate-spin" />
    case 'tests_passed':
      return <TestTube2 size={size} />
    case 'submitted':
      return <Send size={size} />
    case 'failed':
      return <XCircle size={size} />
    case 'blocked':
      return <Ban size={size} />
    case 'skipped':
      return <CircleSlash size={size} />
    default:
      return <CircleDashed size={size} />
  }
}

function PartCell({
  day,
  part,
  info,
  justStarred,
  large,
  onSelect,
}: {
  day: number
  part: number
  info?: PartInfo
  justStarred: boolean
  large: boolean
  onSelect?: (day: number, part: number) => void
}) {
  const s: UiState = info?.ui_state ?? 'unsolved'
  const label = `Day ${day} part ${part}: ${UI_STATE_LABEL[s]}${info?.escalated ? ' (escalated)' : ''}${
    info?.status_reason && (s === 'failed' || s === 'blocked' || s === 'skipped') ? ` — ${info.status_reason}` : ''
  }`
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={() => onSelect?.(day, part)}
      className={cx(
        'relative flex flex-1 items-center justify-center gap-1 rounded-lg border transition-colors',
        large ? 'h-11' : 'h-8',
        STATE_STYLE[s],
        info?.awaiting_approval && 'ring-2 ring-warn',
      )}
    >
      <span className={cx(hasStar(s) && justStarred && 'animate-star-pop')}>
        <PartIcon s={s} size={large ? 22 : 16} />
      </span>
      {info?.escalated && (
        <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-opus shadow-[0_0_8px] shadow-opus" />
      )}
      {s === 'submitted' && info?.state === 'WAITING_FOR_COOLDOWN' && (
        <Hourglass size={12} className="absolute bottom-0.5 right-1" />
      )}
    </button>
  )
}

export function Calendar({
  days,
  dayFrom,
  dayTo,
  lastStar,
  currentDay,
  large = false,
  onSelect,
}: {
  days: DayInfo[]
  dayFrom: number
  dayTo: number
  lastStar: AgentEvent | null
  currentDay: number | null
  large?: boolean
  onSelect?: (day: number, part: number) => void
}) {
  const byDay = new Map(days.map((d) => [d.day, d]))
  const recent = lastStar && Date.now() - new Date(lastStar.created_at).getTime() < 8000 ? lastStar : null
  return (
    <div className={cx('grid grid-cols-5', large ? 'gap-3' : 'gap-2')} role="list" aria-label="Advent calendar">
      {Array.from({ length: 25 }, (_, i) => i + 1).map((d) => {
        const info = byDay.get(d)
        const inRange = d >= dayFrom && d <= dayTo
        const isCurrent = currentDay === d
        const both = info && hasStar(info.parts['1']?.ui_state) && hasStar(info.parts['2']?.ui_state)
        return (
          <div
            key={d}
            role="listitem"
            className={cx(
              'flex flex-col rounded-xl border p-2 transition-all',
              inRange ? 'border-ink-700 bg-ink-800/70' : 'border-ink-800 bg-ink-900/40 opacity-35',
              isCurrent && 'border-sol/80 bg-sol/5 shadow-[0_0_24px_-6px] shadow-sol',
              both && 'border-star/50 shadow-[0_0_22px_-8px] shadow-star',
              large ? 'gap-2 p-3' : 'gap-1.5',
            )}
          >
            <div className="flex items-baseline justify-between gap-1">
              <span className={cx('font-mono font-bold tabular-nums', large ? 'text-2xl' : 'text-sm')}>
                {String(d).padStart(2, '0')}
              </span>
              {info?.title && (
                <span className={cx('truncate text-ink-400', large ? 'text-sm' : 'text-[11px]')} title={info.title}>
                  {info.title}
                </span>
              )}
            </div>
            <div className="flex gap-1.5">
              {[1, 2].map((p) => (
                <PartCell
                  key={p}
                  day={d}
                  part={p}
                  info={info?.parts[String(p)]}
                  large={large}
                  onSelect={onSelect}
                  justStarred={!!recent && recent.day === d && recent.part === p}
                />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function CalendarLegend() {
  const items: UiState[] = ['unsolved', 'solving', 'tests_passed', 'submitted', 'verified', 'previously_completed', 'failed', 'blocked']
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-400">
      {items.map((s) => (
        <span key={s} className="inline-flex items-center gap-1.5">
          <span className={cx('inline-flex h-5 w-5 items-center justify-center rounded border', STATE_STYLE[s].replace('animate-pulse-ring', ''))}>
            <PartIcon s={s} size={12} />
          </span>
          {UI_STATE_LABEL[s]}
        </span>
      ))}
    </div>
  )
}
