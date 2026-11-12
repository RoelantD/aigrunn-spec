import {
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Code2,
  CloudDownload,
  FlaskConical,
  Info,
  Play,
  Send,
  Sparkles,
  Star,
  XCircle,
} from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { AgentEvent } from '../api/types'
import { fmtTime } from '../lib/format'
import { cx } from './ui'

const HIDDEN = new Set(['part.state', 'model.call.finished', 'aoc.fetch'])

function iconFor(e: AgentEvent) {
  if (e.type === 'star.earned') return <Star size={16} className="text-star" fill="currentColor" />
  if (e.type === 'agent.escalation') return <ArrowUpRight size={16} className="text-opus" />
  if (e.type.startsWith('model.')) return <Bot size={16} className={e.data?.model_key === 'escalation' ? 'text-opus' : 'text-sol'} />
  if (e.type === 'agent.code') return <Code2 size={16} className="text-sol" />
  if (e.type.startsWith('test.')) return <FlaskConical size={16} className={e.level === 'error' ? 'text-bad' : e.level === 'success' ? 'text-ok' : 'text-warn'} />
  if (e.type.startsWith('submit.')) return <Send size={16} className={e.level === 'success' ? 'text-ok' : e.level === 'error' ? 'text-bad' : 'text-warn'} />
  if (e.type.startsWith('aoc.')) return <CloudDownload size={16} className="text-ink-300" />
  if (e.type.startsWith('run.')) return <Play size={16} className="text-ink-300" />
  if (e.type === 'agent.analysis') return <Sparkles size={16} className="text-sol" />
  if (e.level === 'error') return <XCircle size={16} className="text-bad" />
  if (e.level === 'warning') return <AlertTriangle size={16} className="text-warn" />
  if (e.level === 'success') return <CheckCircle2 size={16} className="text-ok" />
  return <Info size={16} className="text-ink-400" />
}

export function ActivityFeed({
  events,
  large = false,
  limit = 400,
  showVerbose = false,
}: {
  events: AgentEvent[]
  large?: boolean
  limit?: number
  showVerbose?: boolean
}) {
  const ref = useRef<HTMLOListElement>(null)
  const shown = events.filter((e) => showVerbose || !HIDDEN.has(e.type)).slice(-limit)
  useEffect(() => {
    const el = ref.current
    if (el) el.scrollTop = el.scrollHeight
  }, [shown.length])
  if (!shown.length) {
    return <p className="p-4 text-sm text-ink-400">No activity yet. Events appear here as the agent works.</p>
  }
  let lastKey = ''
  return (
    <ol ref={ref} className="scroll-thin min-h-0 flex-1 overflow-y-auto px-3 py-2" aria-live="polite" aria-label="Agent activity">
      {shown.map((e) => {
        const key = e.day ? `Day ${String(e.day).padStart(2, '0')} - Part ${e.part}` : ''
        const header = key && key !== lastKey ? key : ''
        if (key) lastKey = key
        return (
          <li key={e.id} className="animate-slide-in">
            {header && (
              <div className={cx('mt-3 mb-1 font-mono font-semibold text-ink-300', large ? 'text-lg' : 'text-xs')}>{header}</div>
            )}
            <div
              className={cx(
                'flex items-start gap-2.5 rounded-md px-2 py-1',
                e.type === 'star.earned' && 'bg-star/10',
                e.type === 'agent.escalation' && 'bg-opus/10',
                large ? 'text-xl leading-snug' : 'text-sm',
              )}
            >
              <span className="mt-0.5 shrink-0">{iconFor(e)}</span>
              <span className={cx('min-w-0 flex-1 break-words', e.level === 'error' && 'text-bad', e.level === 'success' && 'text-ok')}>
                {e.message}
              </span>
              {!large && <time className="shrink-0 font-mono text-[11px] text-ink-400">{fmtTime(e.created_at)}</time>}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
