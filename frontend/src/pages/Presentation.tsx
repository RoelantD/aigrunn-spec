import { Bot, Expand, LayoutDashboard, Shrink, Star, TimerReset } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ActivityFeed } from '../components/ActivityFeed'
import { EscalationBanner, ReplayBanner, latestEscalation } from '../components/Banners'
import { Calendar } from '../components/Calendar'
import { CodeBlock, useRevisions } from '../components/CodeInspector'
import { StatusPill } from '../components/RunPanels'
import { cx } from '../components/ui'
import { useElapsed, useRunStream } from '../hooks/useRunStream'
import { useModelNames } from '../lib/config'
import { fmtDuration, fmtUsd } from '../lib/format'
import { useLatestRunId } from './Dashboard'

const TALK_SECONDS = 25 * 60

function DemoClock() {
  const [start, setStart] = useState<number | null>(() => {
    try {
      const v = localStorage.getItem('aps-demo-clock')
      return v ? Number(v) : null
    } catch {
      return null
    }
  })
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [])
  const left = start ? TALK_SECONDS - (now - start) / 1000 : TALK_SECONDS
  const reset = () => {
    const v = Date.now()
    setStart(v)
    try {
      localStorage.setItem('aps-demo-clock', String(v))
    } catch {
      /* ignore */
    }
  }
  return (
    <button
      onClick={reset}
      title="Talk clock (click to start/restart 25:00)"
      className={cx('inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 font-mono text-2xl tabular-nums',
        left < 0 ? 'border-bad text-bad' : left < 180 ? 'border-warn text-warn' : 'border-ink-600 text-ink-300')}
    >
      <TimerReset size={20} />
      {start ? (left < 0 ? '-' : '') + fmtDuration(Math.abs(left)) : '25:00'}
    </button>
  )
}

export function Presentation() {
  const { id } = useParams()
  const runId = useLatestRunId(id)
  const { events, progress, connected, lastStar, codeVersion } = useRunStream(runId)
  const elapsed = useElapsed(progress, events)
  const names = useModelNames()
  const [fs, setFs] = useState(false)
  useEffect(() => {
    const h = () => setFs(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', h)
    return () => document.removeEventListener('fullscreenchange', h)
  }, [])
  const run = progress?.run
  const day = run?.current_day ?? null
  const part = run?.current_part ?? null
  const revs = useRevisions(runId, day, part, codeVersion)
  const rev = revs.at(-1)
  const lastExec = rev?.results.at(-1)
  const curPart = progress?.days.find((d) => d.day === day)?.parts[String(part ?? 1)]
  const model = curPart?.current_model === 'escalation' ? names.escalation : names.workhorse
  const lastStep = [...events].reverse().find((e) => !['part.state', 'aoc.fetch', 'model.call.finished'].includes(e.type))

  if (!runId || !progress) {
    return <div className="flex h-full items-center justify-center text-2xl text-ink-400">Waiting for a run…</div>
  }
  return (
    <div className="flex h-full flex-col">
      <ReplayBanner run={run} />
      <header className="flex items-center gap-6 px-8 pt-6">
        <div>
          <div className="text-sm font-semibold uppercase tracking-[0.25em] text-ink-400">Agentic Advent of Code · {run?.year}</div>
          <div className="mt-1 flex items-center gap-4">
            <StatusPill status={run!.status} connected={connected} />
            <span className="font-mono text-2xl text-ink-300">{fmtDuration(elapsed)}</span>
            <span className="font-mono text-xl text-ink-400">{fmtUsd(run!.total_cost_usd)}</span>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-8">
          <div className="text-right">
            <div className="flex items-center gap-3 text-[96px] font-bold leading-none text-star drop-shadow-[0_0_24px_rgba(251,191,36,0.45)]">
              <Star size={84} fill="currentColor" />
              <span className="tabular-nums">{progress.stars.earned_this_run}</span>
            </div>
            <div className="mt-1 text-base text-ink-400">stars verified by Advent of Code this run · +{progress.stars.previously_completed} earlier</div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <DemoClock />
            <div className="flex gap-2">
              <button
                className="rounded-lg border border-ink-600 p-2 text-ink-300 hover:bg-ink-700"
                aria-label={fs ? 'Exit fullscreen' : 'Enter fullscreen'}
                onClick={() => (fs ? document.exitFullscreen() : document.documentElement.requestFullscreen())}
              >
                {fs ? <Shrink size={20} /> : <Expand size={20} />}
              </button>
              <Link to={`/runs/${runId}`} className="rounded-lg border border-ink-600 p-2 text-ink-300 hover:bg-ink-700" aria-label="Dashboard">
                <LayoutDashboard size={20} />
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] gap-6 p-8 pt-5">
        <div className="flex min-h-0 flex-col gap-5">
          <Calendar days={progress.days} dayFrom={run!.day_from} dayTo={run!.day_to} lastStar={lastStar} currentDay={day} large />
          <EscalationBanner event={latestEscalation(events, day, part)} large />
        </div>
        <div className="flex min-h-0 flex-col gap-4">
          <div className="rounded-2xl border border-ink-700 bg-ink-850/80 p-5">
            <div className="flex items-center gap-3 text-3xl font-semibold">
              <span className="font-mono">{day ? `Day ${String(day).padStart(2, '0')} · Part ${part}` : '—'}</span>
              <span className={cx('ml-auto inline-flex items-center gap-2 text-2xl', curPart?.current_model === 'escalation' ? 'text-opus' : 'text-sol')}>
                <Bot size={28} /> {model}
              </span>
            </div>
            {lastStep && <div className="mt-3 text-2xl leading-snug text-ink-100">{lastStep.message}</div>}
          </div>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-ink-700 bg-ink-850/80">
            <ActivityFeed events={events} large limit={60} />
          </div>
          {rev && (
            <div className="rounded-2xl border border-ink-700 bg-ink-850/80 p-3">
              <div className="mb-2 flex items-center gap-3 px-1 text-base text-ink-300">
                <span className="font-mono">revision {rev.revision}</span>
                {lastExec && (
                  <span className={lastExec.status === 'ok' ? 'text-ok' : 'text-bad'}>
                    {lastExec.kind === 'input' ? 'real input' : 'examples'}: {lastExec.status}
                    {lastExec.answer ? ` → ${lastExec.answer}` : ''} · {(lastExec.duration_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
              <CodeBlock code={rev.code} maxHeight="15rem" fontSize={17} />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
