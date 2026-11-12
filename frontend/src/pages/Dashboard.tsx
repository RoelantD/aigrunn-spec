import { Code2, Gauge, ListTree, MonitorPlay, Plus, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ActivityFeed } from '../components/ActivityFeed'
import { EscalationBanner, ReplayBanner, latestEscalation } from '../components/Banners'
import { Calendar, CalendarLegend } from '../components/Calendar'
import { CodeInspector } from '../components/CodeInspector'
import { MetricsPanel, RunControls, StatusHeader } from '../components/RunPanels'
import { StartRunDialog } from '../components/StartRunDialog'
import { Button, Panel } from '../components/ui'
import { useElapsed, useRunStream } from '../hooks/useRunStream'
import { useConfig, useModelNames } from '../lib/config'

export function useLatestRunId(paramId: string | undefined): number | null {
  const [id, setId] = useState<number | null>(paramId ? Number(paramId) : null)
  useEffect(() => {
    if (paramId) {
      setId(Number(paramId))
      return
    }
    api.runs().then((runs) => {
      const live = runs.find((r) => r.mode === 'live' && r.active) ?? runs.find((r) => r.mode === 'live') ?? runs[0]
      setId(live ? live.id : null)
    })
  }, [paramId])
  return id
}

export function Dashboard() {
  const { id } = useParams()
  const runId = useLatestRunId(id)
  const { events, progress, metrics, connected, lastStar, codeVersion, refresh } = useRunStream(runId)
  const elapsed = useElapsed(progress, events)
  const names = useModelNames()
  const config = useConfig()
  const [startOpen, setStartOpen] = useState(false)
  const [sel, setSel] = useState<{ day: number; part: number } | null>(null)
  const run = progress?.run
  const day = sel?.day ?? run?.current_day ?? null
  const part = sel?.part ?? run?.current_part ?? null
  const understanding = events.filter((e) => e.type === 'agent.analysis' && e.day === day && e.part === part).at(-1)

  return (
    <div className="flex min-h-full flex-col">
      <ReplayBanner run={run} />
      <header className="flex flex-wrap items-center gap-3 border-b border-ink-800 px-6 py-3">
        <Sparkles className="text-star" size={22} />
        <h1 className="text-lg font-semibold tracking-tight">Agentic Puzzle Solver</h1>
        <span className="text-sm text-ink-400">Spec-Driven · Microsoft Foundry · Azure Dynamic Sessions</span>
        <nav className="ml-auto flex items-center gap-2">
          <Link to="/runs">
            <Button variant="ghost"><ListTree size={16} /> Runs</Button>
          </Link>
          {runId && (
            <Link to={`/present/${runId}`}>
              <Button variant="ghost"><MonitorPlay size={16} /> Presentation</Button>
            </Link>
          )}
          <Button variant="primary" onClick={() => setStartOpen(true)}>
            <Plus size={16} /> New live run
          </Button>
        </nav>
      </header>
      <StartRunDialog open={startOpen} onOpenChange={setStartOpen} config={config} />

      {!runId && (
        <div className="m-auto max-w-lg p-10 text-center text-ink-300">
          <p className="text-lg">No runs yet.</p>
          <p className="mt-2 text-sm text-ink-400">Start a live run to let the agent solve Advent of Code 2024 autonomously.</p>
          <Button className="mt-6" variant="primary" onClick={() => setStartOpen(true)}><Plus size={16} /> New live run</Button>
        </div>
      )}

      {runId && progress && (
        <main className="flex min-h-0 flex-1 flex-col gap-4 p-4 lg:p-6">
          <div className="rounded-2xl border border-ink-700 bg-ink-850/80 p-4">
            <StatusHeader progress={progress} elapsed={elapsed} connected={connected} names={names} />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
              <RunControls progress={progress} onChanged={refresh} />
              <span className="text-xs text-ink-400">Run #{progress.run.id} · {progress.run.auto_submit ? 'automatic submission authorized' : 'manual approval mode'}</span>
            </div>
          </div>
          <EscalationBanner event={latestEscalation(events, day, part)} />
          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
            <div className="flex min-h-0 flex-col gap-4">
              <Panel title="Calendar" actions={<CalendarLegend />}>
                <div className="p-3">
                  <Calendar
                    days={progress.days}
                    dayFrom={progress.run.day_from}
                    dayTo={progress.run.day_to}
                    lastStar={lastStar}
                    currentDay={progress.run.current_day}
                    onSelect={(d, p) => setSel({ day: d, part: p })}
                  />
                </div>
              </Panel>
              <Panel title="Live activity" className="min-h-[22rem] flex-1">
                <ActivityFeed events={events} />
              </Panel>
            </div>
            <div className="flex min-h-0 flex-col gap-4">
              {understanding && (
                <Panel title={`Understanding · Day ${day} Part ${part}`} icon={<Sparkles size={14} />}>
                  <div className="space-y-1.5 p-4 text-sm">
                    <p>{understanding.data.summary}</p>
                    <p className="text-ink-300"><span className="text-ink-400">Approach: </span>{understanding.data.algorithm}</p>
                    <p className="font-mono text-xs text-ink-400">{understanding.data.complexity} · {understanding.data.model}</p>
                    {understanding.data.diagnosis && <p className="text-warn">Diagnosis: {understanding.data.diagnosis}</p>}
                  </div>
                </Panel>
              )}
              <Panel title="Code inspector" icon={<Code2 size={14} />} className="min-h-[24rem] flex-1">
                <CodeInspector runId={runId} day={day} part={part} version={codeVersion} names={names} />
              </Panel>
              <Panel title="Inference metrics" icon={<Gauge size={14} />}>
                <MetricsPanel metrics={metrics} />
              </Panel>
            </div>
          </div>
        </main>
      )}
    </div>
  )
}
