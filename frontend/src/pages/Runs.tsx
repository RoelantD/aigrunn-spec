import { ArrowLeft, History, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Run } from '../api/types'
import { StatusPill } from '../components/RunPanels'
import { ConnectionChecks, StartRunDialog } from '../components/StartRunDialog'
import { Badge, Button, Panel } from '../components/ui'
import { useConfig } from '../lib/config'
import { fmtDuration, fmtUsd } from '../lib/format'

export function Runs() {
  const [runs, setRuns] = useState<Run[]>([])
  const [notice, setNotice] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const config = useConfig()
  const nav = useNavigate()
  const load = () => api.runs().then(setRuns).catch(() => {})
  useEffect(() => {
    load()
  }, [])
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4 p-6">
      <div className="flex items-center gap-3">
        <Link to="/"><Button variant="ghost"><ArrowLeft size={16} /> Dashboard</Button></Link>
        <h1 className="text-xl font-semibold">Runs</h1>
        <Button className="ml-auto" variant="primary" onClick={() => setOpen(true)}><Plus size={16} /> New live run</Button>
      </div>
      <StartRunDialog open={open} onOpenChange={setOpen} config={config} />
      {notice && <p className="rounded-lg border border-sol/40 bg-sol/10 p-3 text-sm text-sol">{notice}</p>}
      <Panel title="Environment">
        <div className="grid gap-4 p-4 text-sm md:grid-cols-2">
          <div className="space-y-1 text-ink-300">
            <div>Workhorse: <b>{config?.workhorse.display_name}</b> <span className="font-mono text-xs text-ink-400">({config?.workhorse.deployment})</span> {config?.workhorse.configured ? <Badge tone="ok">configured</Badge> : <Badge tone="bad">missing</Badge>}</div>
            <div>Escalation: <b>{config?.escalation.display_name}</b> <span className="font-mono text-xs text-ink-400">({config?.escalation.deployment})</span> {config?.escalation.configured ? <Badge tone="ok">configured</Badge> : <Badge tone="bad">missing</Badge>}</div>
            <div>Sandbox: Azure Container Apps Dynamic Sessions {config?.sandbox.configured ? <Badge tone="ok">configured</Badge> : <Badge tone="bad">missing</Badge>}</div>
            <div>Advent of Code session: {config?.aoc_session_configured ? <Badge tone="ok">configured</Badge> : <Badge tone="bad">missing</Badge>}</div>
            <div className="text-xs text-ink-400">Data directory: <span className="font-mono">{config?.data_dir}</span></div>
          </div>
          <ConnectionChecks />
        </div>
      </Panel>
      <Panel title="Previous runs">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-ink-400">
            <tr className="border-b border-ink-700">
              <th className="px-4 py-2">#</th><th>Mode</th><th>Year · days</th><th>Status</th><th>Elapsed</th><th>Cost</th><th>Created</th><th />
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} className="cursor-pointer border-b border-ink-800 hover:bg-ink-800/60" onClick={() => nav(`/runs/${r.id}`)}>
                <td className="px-4 py-2 font-mono">{r.id}</td>
                <td>{r.mode === 'replay' ? <Badge tone="warn"><History size={12} /> replay of #{r.source_run_id}</Badge> : <Badge tone="sol">live</Badge>}</td>
                <td>{r.year} · {r.day_from}–{r.day_to}</td>
                <td><StatusPill status={r.status} connected /></td>
                <td className="font-mono">{fmtDuration(r.elapsed_seconds)}</td>
                <td className="font-mono">{fmtUsd(r.total_cost_usd)}</td>
                <td className="text-ink-400">{r.created_at ? new Date(r.created_at).toLocaleString() : ''}</td>
                <td className="whitespace-nowrap pr-3 text-right" onClick={(e) => e.stopPropagation()}>
                  {r.mode === 'live' && (
                    <Button variant="ghost" title="Replay this recorded run (clearly labelled, no live calls)" onClick={async () => {
                      const rep = await api.replay(r.id, 10)
                      nav(`/runs/${rep.id}`)
                    }}>
                      <History size={15} /> Replay
                    </Button>
                  )}
                  {!r.active && (
                    <Button variant="ghost" aria-label={`Delete run ${r.id}`} onClick={async () => {
                      if (!confirm(`Delete local data for run #${r.id}? Advent of Code account progress is not affected.`)) return
                      const res = await api.deleteRun(r.id)
                      setNotice(res.notice)
                      load()
                    }}>
                      <Trash2 size={15} />
                    </Button>
                  )}
                </td>
              </tr>
            ))}
            {!runs.length && (
              <tr><td colSpan={8} className="px-4 py-6 text-center text-ink-400">No runs recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      </Panel>
    </div>
  )
}
