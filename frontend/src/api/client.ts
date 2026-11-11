import type { CheckResult, Metrics, Progress, PublicConfig, Revision, Run, Submission } from './types'

const BASE = '/api'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export interface CreateRunBody {
  calendar_url: string
  day_from: number
  day_to: number
  auto_submit: boolean
  authorize_submission: boolean
  config?: Record<string, unknown>
}

export const api = {
  config: () => req<PublicConfig>('GET', '/config'),
  verify: (checks?: string[]) =>
    req<{ overall: string; checks: CheckResult[] }>('POST', '/connections/verify', { checks }),
  runs: () => req<Run[]>('GET', '/runs'),
  run: (id: number) => req<Run>('GET', `/runs/${id}`),
  createRun: (body: CreateRunBody) => req<Run>('POST', '/runs', body),
  control: (id: number, action: 'start' | 'pause' | 'resume' | 'stop') =>
    req<{ ok: boolean }>('POST', `/runs/${id}/${action}`),
  retryPart: (id: number, day: number, part: number) =>
    req<{ ok: boolean }>('POST', `/runs/${id}/parts/${day}/${part}/retry`),
  approve: (id: number, day: number, part: number) =>
    req<{ ok: boolean }>('POST', `/runs/${id}/parts/${day}/${part}/approve`),
  progress: (id: number) => req<Progress>('GET', `/runs/${id}/progress`),
  revisions: (id: number, day: number, part: number) =>
    req<Revision[]>('GET', `/runs/${id}/parts/${day}/${part}/revisions`),
  submissions: (id: number) => req<Submission[]>('GET', `/runs/${id}/submissions`),
  metrics: (id: number) => req<Metrics>('GET', `/runs/${id}/metrics`),
  replay: (id: number, speed: number) => req<Run>('POST', `/runs/${id}/replay`, { speed }),
  deleteRun: (id: number) => req<{ ok: boolean; notice: string }>('DELETE', `/runs/${id}`),
}
