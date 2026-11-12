import { CheckCircle2, Clock, XCircle } from 'lucide-react'
import { Highlight, themes } from 'prism-react-renderer'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { ExecResult, Revision } from '../api/types'
import { cx } from './ui'

export function CodeBlock({ code, maxHeight, fontSize = 13 }: { code: string; maxHeight?: string; fontSize?: number }) {
  return (
    <Highlight theme={themes.nightOwl} code={code.replace(/\n$/, '')} language="python">
      {({ className, style, tokens, getLineProps, getTokenProps }) => (
        <pre
          className={cx(className, 'scroll-thin overflow-auto rounded-lg p-3 font-mono')}
          style={{ ...style, background: '#070b16', maxHeight, fontSize }}
        >
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              <span className="mr-4 inline-block w-7 select-none text-right text-ink-600">{i + 1}</span>
              {line.map((token, k) => (
                <span key={k} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  )
}

function ResultSummary({ r }: { r: ExecResult }) {
  const ok = r.status === 'ok' && r.cases.every((c) => c.passed !== false && !c.error)
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900/70 p-3 text-sm">
      <div className="flex items-center gap-2">
        {r.timed_out ? <Clock size={15} className="text-warn" /> : ok ? <CheckCircle2 size={15} className="text-ok" /> : <XCircle size={15} className="text-bad" />}
        <span className="font-medium">{r.kind === 'examples' ? 'Example tests' : 'Real input'}</span>
        <span className="text-ink-400">
          {r.status}
          {r.timed_out ? ' (timeout)' : ''} · {(r.duration_ms / 1000).toFixed(2)}s
        </span>
        <span className="ml-auto truncate font-mono text-[11px] text-ink-600" title="sandbox session">{r.correlation_id}</span>
      </div>
      {r.kind === 'examples' && r.cases.length > 0 && (
        <table className="mt-2 w-full text-left text-xs">
          <thead className="text-ink-400">
            <tr>
              <th className="py-1 font-medium">#</th>
              <th className="font-medium">expected</th>
              <th className="font-medium">actual</th>
              <th className="font-medium">result</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {r.cases.map((c) => (
              <tr key={c.index} className="border-t border-ink-800 align-top">
                <td className="py-1">{c.index + 1}</td>
                <td>{c.reliable ? c.expected : <span className="text-ink-400">n/a</span>}</td>
                <td className="max-w-[16rem] truncate">{c.actual ?? '—'}</td>
                <td className={c.passed ? 'text-ok' : 'text-bad'}>{c.passed ? 'pass' : c.error ? c.error.split('\n')[0] : 'fail'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {r.kind === 'input' && (
        <div className="mt-2 font-mono text-sm">
          {r.answer ? (
            <>
              candidate answer: <span className="text-star">{r.answer}</span>
            </>
          ) : (
            <span className="text-bad">{r.cases[0]?.error?.split('\n')[0] ?? 'no answer'}</span>
          )}
        </div>
      )}
      {(r.stderr || r.stdout) && (
        <details className="mt-2 text-xs text-ink-400">
          <summary className="cursor-pointer">output</summary>
          <pre className="scroll-thin mt-1 max-h-40 overflow-auto whitespace-pre-wrap font-mono">{[r.stdout, r.stderr].filter(Boolean).join('\n')}</pre>
        </details>
      )}
    </div>
  )
}

export function useRevisions(runId: number | null, day: number | null, part: number | null, version: number) {
  const [revs, setRevs] = useState<Revision[]>([])
  useEffect(() => {
    if (runId == null || day == null || part == null) {
      setRevs([])
      return
    }
    let alive = true
    api.revisions(runId, day, part).then((r) => alive && setRevs(r)).catch(() => {})
    return () => {
      alive = false
    }
  }, [runId, day, part, version])
  return revs
}

export function CodeInspector({
  runId,
  day,
  part,
  version,
  names,
}: {
  runId: number | null
  day: number | null
  part: number | null
  version: number
  names: { workhorse: string; escalation: string }
}) {
  const revs = useRevisions(runId, day, part, version)
  const [sel, setSel] = useState<number | null>(null)
  useEffect(() => setSel(null), [day, part])
  if (day == null || part == null) return <p className="p-4 text-sm text-ink-400">Select a part in the calendar.</p>
  if (!revs.length) return <p className="p-4 text-sm text-ink-400">No code generated yet for Day {day} Part {part}.</p>
  const current = revs.find((r) => r.revision === sel) ?? revs[revs.length - 1]
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-3">
      <div className="flex flex-wrap items-center gap-1.5" role="tablist" aria-label="Code revisions">
        <span className="mr-1 text-xs text-ink-400">Day {day} · Part {part} · revisions</span>
        {revs.map((r) => (
          <button
            key={r.revision}
            role="tab"
            aria-selected={r.revision === current.revision}
            onClick={() => setSel(r.revision)}
            className={cx(
              'rounded-md border px-2 py-0.5 font-mono text-xs',
              r.revision === current.revision ? 'border-sol bg-sol/15 text-sol' : 'border-ink-600 text-ink-300 hover:bg-ink-700',
              r.model_key === 'escalation' && 'border-opus/60 text-opus',
            )}
            title={r.model_key === 'escalation' ? names.escalation : names.workhorse}
          >
            r{r.revision}
          </button>
        ))}
        <span className={cx('ml-auto text-xs', current.model_key === 'escalation' ? 'text-opus' : 'text-sol')}>
          {current.model_key === 'escalation' ? names.escalation : names.workhorse}
        </span>
      </div>
      <CodeBlock code={current.code} maxHeight="26rem" />
      <div className="flex flex-col gap-2">
        {current.results.map((r, i) => (
          <ResultSummary key={i} r={r} />
        ))}
      </div>
    </div>
  )
}
