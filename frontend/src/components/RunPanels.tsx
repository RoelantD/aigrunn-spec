import { Activity, Bot, Pause, Play, RotateCcw, Square, Star, ThumbsUp, Timer, Wallet, Wifi, WifiOff } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import type { Metrics, Progress } from '../api/types'
import { fmtDuration, fmtTokens, fmtUsd, modelName } from '../lib/format'
import { Badge, Button, Stat, cx } from './ui'

const STATUS_TONE: Record<string, string> = {
  running: 'ok',
  paused: 'warn',
  created: 'neutral',
  stopped: 'neutral',
  completed: 'sol',
  budget_exhausted: 'bad',
  failed: 'bad',
}

export function StatusPill({ status, connected }: { status: string; connected: boolean }) {
  const live = status === 'running'
  return (
    <span className="inline-flex items-center gap-2">
      <Badge tone={STATUS_TONE[status] ?? 'neutral'} className="text-sm uppercase tracking-wider">
        {live && <span className="h-2 w-2 animate-pulse rounded-full bg-ok" />}
        {status.replace('_', ' ')}
      </Badge>
      {connected ? (
        <Wifi size={15} className="text-ok" aria-label="live stream connected" />
      ) : (
        <WifiOff size={15} className="text-bad" aria-label="live stream disconnected" />
      )}
    </span>
  )
}

export function StatusHeader({
  progress,
  elapsed,
  connected,
  names,
}: {
  progress: Progress
  elapsed: number
  connected: boolean
  names: { workhorse: string; escalation: string }
}) {
  const r = progress.run
  const cur = progress.days.find((d) => d.day === r.current_day)?.parts[String(r.current_part ?? 1)]
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4 xl:grid-cols-8">
      <Stat label="Calendar" value={`${r.year}`} sub={`days ${r.day_from}–${r.day_to}`} />
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">Status</div>
        <div className="mt-1">
          <StatusPill status={r.status} connected={connected} />
        </div>
        {r.stop_reason && r.status !== 'running' && <div className="mt-1 truncate text-xs text-ink-400" title={r.stop_reason}>{r.stop_reason}</div>}
      </div>
      <Stat
        label="Now solving"
        value={r.current_day ? `Day ${String(r.current_day).padStart(2, '0')} · P${r.current_part}` : '—'}
        sub={cur ? cur.state.replaceAll('_', ' ').toLowerCase() : undefined}
      />
      <Stat
        label="Model"
        value={<span className={cur?.current_model === 'escalation' ? 'text-opus' : 'text-sol'}>{modelName(cur?.current_model, names)}</span>}
      />
      <Stat
        label="Verified stars"
        tone="text-star"
        value={
          <span className="inline-flex items-center gap-1.5">
            <Star size={18} fill="currentColor" /> {progress.stars.earned_this_run}
          </span>
        }
        sub={`+${progress.stars.previously_completed} previously completed`}
      />
      <Stat label="Failed / blocked" value={`${progress.failed} / ${progress.blocked}`} tone={progress.failed ? 'text-bad' : undefined} />
      <Stat label="Attempts" value={progress.attempts} sub={`${r.total_model_calls} model calls`} />
      <Stat label="Elapsed · cost" value={fmtDuration(elapsed)} sub={`${fmtUsd(r.total_cost_usd)} estimated`} />
    </div>
  )
}

export function MetricsPanel({ metrics }: { metrics: Metrics | null }) {
  if (!metrics) return null
  const rows = Object.entries(metrics.by_model)
  return (
    <div className="p-3 text-sm">
      {rows.length === 0 && <p className="text-ink-400">No model calls yet.</p>}
      {rows.map(([k, m]) => (
        <div key={k} className="mb-3 rounded-lg border border-ink-700 bg-ink-900/50 p-3">
          <div className={cx('mb-2 flex items-center gap-2 font-semibold', k === 'escalation' ? 'text-opus' : 'text-sol')}>
            <Bot size={16} /> {m.display_name}
            {metrics.pricing_configured[k] === false && <Badge tone="warn">pricing not configured</Badge>}
          </div>
          <div className="grid grid-cols-3 gap-2">
            <Stat label="Calls" value={m.calls} sub={m.errors ? `${m.errors} errors` : undefined} />
            <Stat label="Tokens in/out" value={`${fmtTokens(m.input_tokens)} / ${fmtTokens(m.output_tokens)}`} sub={m.reasoning_tokens ? `${fmtTokens(m.reasoning_tokens)} reasoning` : undefined} />
            <Stat label="Avg latency · cost" value={`${(m.avg_latency_ms / 1000).toFixed(1)}s`} sub={fmtUsd(m.cost_usd)} />
          </div>
        </div>
      ))}
      <div className="flex items-center gap-4 text-xs text-ink-400">
        <span className="inline-flex items-center gap-1"><Activity size={13} /> {metrics.total_model_calls} calls</span>
        <span className="inline-flex items-center gap-1"><Wallet size={13} /> {fmtUsd(metrics.total_cost_usd)}</span>
        <span className="inline-flex items-center gap-1 text-opus"><Timer size={13} /> {metrics.escalations} escalation(s)</span>
      </div>
    </div>
  )
}

export function RunControls({ progress, onChanged }: { progress: Progress; onChanged: () => void }) {
  const r = progress.run
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  if (r.mode === 'replay') return null
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setErr(null)
    try {
      await fn()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
      onChanged()
    }
  }
  const pending = progress.days.flatMap((d) =>
    Object.entries(d.parts)
      .filter(([, p]) => p.awaiting_approval)
      .map(([k, p]) => ({ day: d.day, part: Number(k), answer: p.candidate_answer })),
  )
  const retryable = progress.days.flatMap((d) =>
    Object.entries(d.parts)
      .filter(([, p]) => ['failed', 'blocked', 'skipped'].includes(p.ui_state))
      .map(([k]) => ({ day: d.day, part: Number(k) })),
  )
  return (
    <div className="flex flex-wrap items-center gap-2">
      {r.status === 'created' && (
        <Button variant="primary" disabled={busy} onClick={() => act(() => api.control(r.id, 'start'))}>
          <Play size={16} /> Start
        </Button>
      )}
      {r.status === 'running' && (
        <Button disabled={busy} onClick={() => act(() => api.control(r.id, 'pause'))}>
          <Pause size={16} /> Pause
        </Button>
      )}
      {r.status === 'paused' && (
        <Button variant="primary" disabled={busy} onClick={() => act(() => api.control(r.id, 'resume'))}>
          <Play size={16} /> Resume
        </Button>
      )}
      {['running', 'paused', 'created'].includes(r.status) && (
        <Button variant="danger" disabled={busy} onClick={() => act(() => api.control(r.id, 'stop'))}>
          <Square size={14} /> Stop
        </Button>
      )}
      {pending.map((p) => (
        <Button key={`${p.day}-${p.part}`} variant="primary" disabled={busy} onClick={() => act(() => api.approve(r.id, p.day, p.part))}>
          <ThumbsUp size={15} /> Submit {p.answer} for Day {p.day} P{p.part}
        </Button>
      ))}
      {r.status !== 'running' &&
        retryable.slice(0, 3).map((p) => (
          <Button key={`r${p.day}-${p.part}`} variant="ghost" disabled={busy} onClick={() => act(() => api.retryPart(r.id, p.day, p.part))}>
            <RotateCcw size={14} /> Retry D{p.day} P{p.part}
          </Button>
        ))}
      {err && <span className="text-sm text-bad">{err}</span>}
    </div>
  )
}
