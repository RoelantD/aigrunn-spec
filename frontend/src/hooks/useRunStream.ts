import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { AgentEvent, Metrics, Progress } from '../api/types'

const REFRESH_TYPES = new Set([
  'part.state', 'star.earned', 'submit.result', 'submit.reconciled', 'aoc.previously_completed', 'agent.escalation',
  'test.result', 'exec.input', 'model.call.finished', 'run.started', 'run.resumed', 'run.paused', 'run.stopped',
  'run.completed', 'run.failed', 'run.budget_exhausted', 'run.interrupted', 'part.retry', 'submit.awaiting_approval',
  'agent.code',
])

export interface RunStream {
  events: AgentEvent[]
  progress: Progress | null
  metrics: Metrics | null
  connected: boolean
  lastStar: AgentEvent | null
  codeVersion: number
  refresh: () => void
}

/** Subscribes to the run's SSE stream, resuming from the last seen event id after reconnects (FR-031). */
export function useRunStream(runId: number | null): RunStream {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [progress, setProgress] = useState<Progress | null>(null)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [connected, setConnected] = useState(false)
  const [lastStar, setLastStar] = useState<AgentEvent | null>(null)
  const [codeVersion, setCodeVersion] = useState(0)
  const lastId = useRef(0)
  const timer = useRef<number | null>(null)

  const refresh = useCallback(() => {
    if (runId == null) return
    api.progress(runId).then(setProgress).catch(() => {})
    api.metrics(runId).then(setMetrics).catch(() => {})
  }, [runId])

  const scheduleRefresh = useCallback(() => {
    if (timer.current != null) return
    timer.current = window.setTimeout(() => {
      timer.current = null
      refresh()
    }, 250)
  }, [refresh])

  useEffect(() => {
    setEvents([])
    setProgress(null)
    setMetrics(null)
    setLastStar(null)
    lastId.current = 0
    if (runId == null) return
    refresh()
    let es: EventSource | null = null
    let closed = false
    let retry: number | null = null

    const open = () => {
      // Browsers send Last-Event-ID automatically on auto-reconnect; after a manual reopen we pass after_id.
      es = new EventSource(`/api/runs/${runId}/events/stream?after_id=${lastId.current}`)
      es.onopen = () => setConnected(true)
      es.onmessage = (msg) => {
        const ev = JSON.parse(msg.data) as AgentEvent
        if (ev.id <= lastId.current) return
        lastId.current = ev.id
        setEvents((prev) => (prev.length > 3000 ? [...prev.slice(-2500), ev] : [...prev, ev]))
        if (ev.type === 'star.earned') setLastStar(ev)
        if (ev.type === 'agent.code' || ev.type === 'test.result' || ev.type === 'exec.input') {
          setCodeVersion((v) => v + 1)
        }
        if (REFRESH_TYPES.has(ev.type)) scheduleRefresh()
      }
      es.onerror = () => {
        setConnected(false)
        es?.close()
        if (!closed) retry = window.setTimeout(open, 1500)
      }
    }
    open()
    return () => {
      closed = true
      es?.close()
      if (retry) window.clearTimeout(retry)
    }
  }, [runId, refresh, scheduleRefresh])

  return { events, progress, metrics, connected, lastStar, codeVersion, refresh }
}

/** Elapsed run time: persisted seconds + time since the latest start/resume while active. */
export function useElapsed(progress: Progress | null, events: AgentEvent[]): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(t)
  }, [])
  if (!progress) return 0
  const base = progress.run.elapsed_seconds || 0
  if (progress.run.status !== 'running') return base
  const start = [...events].reverse().find((e) => e.type === 'run.started' || e.type === 'run.resumed')
  if (!start) return base
  return base + Math.max(0, (now - new Date(start.created_at).getTime()) / 1000)
}
