export type RunStatus = 'created' | 'running' | 'paused' | 'stopped' | 'completed' | 'budget_exhausted' | 'failed'

export type UiState =
  | 'unsolved'
  | 'solving'
  | 'tests_passed'
  | 'submitted'
  | 'verified'
  | 'previously_completed'
  | 'failed'
  | 'blocked'
  | 'skipped'

export interface Run {
  id: number
  mode: 'live' | 'replay'
  source_run_id: number | null
  year: number
  day_from: number
  day_to: number
  status: RunStatus
  stop_reason: string | null
  auto_submit: boolean
  config: Record<string, unknown>
  current_day: number | null
  current_part: number | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
  elapsed_seconds: number
  total_cost_usd: number
  total_input_tokens: number
  total_output_tokens: number
  total_reasoning_tokens: number
  total_model_calls: number
  active: boolean
}

export interface PartInfo {
  state: string
  ui_state: UiState
  previously_completed: boolean
  tests_passed: boolean
  candidate_answer: string | null
  accepted_answer: string | null
  attempts_used: number
  submissions_used: number
  current_model: string | null
  escalated: boolean
  status_reason: string | null
  awaiting_approval: boolean
}

export interface DayInfo {
  day: number
  title: string | null
  parts: Record<string, PartInfo>
}

export interface Progress {
  run: Run
  days: DayInfo[]
  stars: { earned_this_run: number; previously_completed: number; total: number }
  failed: number
  blocked: number
  attempts: number
}

export interface AgentEvent {
  id: number
  run_id: number
  type: string
  day: number | null
  part: number | null
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  data: Record<string, any>
  replay: boolean
  created_at: string
}

export interface CaseResult {
  index: number
  expected?: string | null
  actual?: string | null
  passed?: boolean
  error?: string | null
  duration_ms?: number | null
  reliable?: boolean
}

export interface ExecResult {
  kind: 'examples' | 'input' | 'probe'
  status: string
  cases: CaseResult[]
  answer: string | null
  stdout: string
  stderr: string
  duration_ms: number
  timed_out: boolean
  correlation_id: string
}

export interface Revision {
  revision: number
  model_key: string
  code: string
  sha256: string
  created_at: string | null
  results: ExecResult[]
}

export interface ModelMetrics {
  display_name: string
  calls: number
  input_tokens: number
  output_tokens: number
  reasoning_tokens: number
  avg_latency_ms: number
  cost_usd: number
  errors: number
}

export interface Metrics {
  run_id: number
  total_cost_usd: number
  total_model_calls: number
  escalations: number
  pricing_configured: Record<string, boolean>
  by_model: Record<string, ModelMetrics>
}

export interface PublicConfig {
  version: string
  data_dir: string
  aoc_session_configured: boolean
  aoc_contact_configured: boolean
  workhorse: { display_name: string; deployment: string; configured: boolean; auth: string; priced: boolean }
  escalation: { display_name: string; deployment: string; configured: boolean; auth: string; priced: boolean }
  sandbox: { configured: boolean; kind: string }
  run_defaults: Record<string, any>
}

export interface CheckResult {
  name: string
  status: 'pass' | 'fail' | 'skipped'
  detail: string
  latency_ms: number
}

export interface Submission {
  id: number
  day: number
  part: number
  answer: string
  outcome: string
  message: string | null
  wait_seconds: number | null
  submitted_at: string | null
}
