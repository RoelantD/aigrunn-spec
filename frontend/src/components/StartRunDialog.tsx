import { AlertTriangle, PlugZap, Rocket, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { CheckResult, PublicConfig } from '../api/types'
import { Badge, Button, Dialog, Switch } from './ui'

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-ink-300">{label}</span>
      {children}
      {hint && <span className="text-xs text-ink-400">{hint}</span>}
    </label>
  )
}

const input = 'rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 font-mono text-sm focus:border-sol focus:outline-none'

export function ConnectionChecks({ compact = false }: { compact?: boolean }) {
  const [checks, setChecks] = useState<CheckResult[] | null>(null)
  const [busy, setBusy] = useState(false)
  return (
    <div className="flex flex-col gap-2">
      <Button
        disabled={busy}
        onClick={async () => {
          setBusy(true)
          try {
            setChecks((await api.verify()).checks)
          } finally {
            setBusy(false)
          }
        }}
      >
        <PlugZap size={16} /> {busy ? 'Checking connections…' : 'Verify connections'}
      </Button>
      {checks && (
        <ul className="flex flex-col gap-1 text-xs">
          {checks.map((c) => (
            <li key={c.name} className="flex items-start gap-2">
              <Badge tone={c.status === 'pass' ? 'ok' : c.status === 'fail' ? 'bad' : 'neutral'}>{c.status}</Badge>
              <span className="font-semibold">{c.name}</span>
              {!compact && <span className="text-ink-400">{c.detail}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function StartRunDialog({
  open,
  onOpenChange,
  config,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  config: PublicConfig | null
}) {
  const nav = useNavigate()
  const d = config?.run_defaults ?? {}
  const [url, setUrl] = useState('https://adventofcode.com/2024')
  const [from, setFrom] = useState(1)
  const [to, setTo] = useState(25)
  const [autoSubmit, setAutoSubmit] = useState(true)
  const [authorized, setAuthorized] = useState(false)
  const [attempts, setAttempts] = useState<number>(d.max_attempts_per_part ?? 6)
  const [escalateAfter, setEscalateAfter] = useState<number>(d.escalate_after_failures ?? 3)
  const [spend, setSpend] = useState<number>(d.max_spend_usd ?? 20)
  const [timeout, setTimeoutS] = useState<number>(d.exec_timeout_s ?? 30)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const canStart = !busy && (!autoSubmit || authorized)

  const submit = async () => {
    setBusy(true)
    setErr(null)
    try {
      const run = await api.createRun({
        calendar_url: url.trim(),
        day_from: from,
        day_to: to,
        auto_submit: autoSubmit,
        authorize_submission: autoSubmit && authorized,
        config: { max_attempts_per_part: attempts, escalate_after_failures: escalateAfter, max_spend_usd: spend, exec_timeout_s: timeout },
      })
      await api.control(run.id, 'start')
      onOpenChange(false)
      nav(`/runs/${run.id}`)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const missing = config
    ? [
        !config.aoc_session_configured && 'Advent of Code session',
        !config.workhorse.configured && config.workhorse.display_name,
        !config.sandbox.configured && 'Dynamic Sessions pool',
      ].filter(Boolean)
    : []

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Start a live run" description="Solves real puzzles with real models in the sandbox and submits to the real website.">
      <div className="flex flex-col gap-4">
        {missing.length > 0 && (
          <div className="flex gap-2 rounded-lg border border-bad/50 bg-bad/10 p-3 text-sm text-bad">
            <AlertTriangle size={18} className="shrink-0" /> Not configured: {missing.join(', ')}. See demo/PRESENTER_GUIDE.md.
          </div>
        )}
        <Field label="Calendar URL">
          <input className={input} value={url} onChange={(e) => setUrl(e.target.value)} aria-label="Calendar URL" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="First day">
            <input className={input} type="number" min={1} max={25} value={from} onChange={(e) => setFrom(+e.target.value)} />
          </Field>
          <Field label="Last day">
            <input className={input} type="number" min={1} max={25} value={to} onChange={(e) => setTo(+e.target.value)} />
          </Field>
          <Field label="Attempts per part">
            <input className={input} type="number" min={1} max={20} value={attempts} onChange={(e) => setAttempts(+e.target.value)} />
          </Field>
          <Field label="Escalate after failures" hint="0 disables escalation">
            <input className={input} type="number" min={0} max={20} value={escalateAfter} onChange={(e) => setEscalateAfter(+e.target.value)} />
          </Field>
          <Field label="Max spend (USD)">
            <input className={input} type="number" min={0} step={1} value={spend} onChange={(e) => setSpend(+e.target.value)} />
          </Field>
          <Field label="Execution timeout (s)">
            <input className={input} type="number" min={5} max={220} value={timeout} onChange={(e) => setTimeoutS(+e.target.value)} />
          </Field>
        </div>

        <div className="rounded-xl border border-ink-600 bg-ink-900/60 p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold">Automatic answer submission</div>
              <div className="text-xs text-ink-400">Submits candidate answers to adventofcode.com without asking per answer.</div>
            </div>
            <Switch id="auto-submit" label="Automatic answer submission" checked={autoSubmit} onCheckedChange={setAutoSubmit} />
          </div>
          {autoSubmit ? (
            <label className="mt-3 flex cursor-pointer items-start gap-3 rounded-lg border border-warn/40 bg-warn/10 p-3 text-sm">
              <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[#fb923c]" checked={authorized} onChange={(e) => setAuthorized(e.target.checked)} />
              <span>
                <ShieldCheck size={15} className="mr-1 inline text-warn" />I authorize this application to submit answers to Advent of Code on my behalf for this
                entire run. Each distinct answer is submitted at most once; server cooldowns are respected.
              </span>
            </label>
          ) : (
            <p className="mt-3 rounded-lg border border-ink-600 bg-ink-800 p-3 text-sm text-ink-300">
              Manual-approval mode: each candidate answer waits for you. Without submission, Advent of Code will not unlock
              Part 2, so progression stops at every Part 1 until you approve.
            </p>
          )}
        </div>

        <ConnectionChecks />
        {err && <p className="text-sm text-bad">{err}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="primary" disabled={!canStart} onClick={submit}>
            <Rocket size={16} /> {busy ? 'Starting…' : 'Start live run'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
