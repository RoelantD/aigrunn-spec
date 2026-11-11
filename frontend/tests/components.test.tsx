import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { AgentEvent, DayInfo, PartInfo, Run, UiState } from '../src/api/types'
import { ActivityFeed } from '../src/components/ActivityFeed'
import { EscalationBanner, ReplayBanner, latestEscalation } from '../src/components/Banners'
import { Calendar } from '../src/components/Calendar'
import { hasStar } from '../src/lib/format'

const part = (ui_state: UiState, extra: Partial<PartInfo> = {}): PartInfo => ({
  state: 'X', ui_state, previously_completed: ui_state === 'previously_completed', tests_passed: false,
  candidate_answer: null, accepted_answer: null, attempts_used: 0, submissions_used: 0, current_model: null,
  escalated: false, status_reason: null, awaiting_approval: false, ...extra,
})

const ev = (id: number, type: string, message: string, extra: Partial<AgentEvent> = {}): AgentEvent => ({
  id, run_id: 1, type, day: 2, part: 1, level: 'info', message, data: {}, replay: false,
  created_at: new Date().toISOString(), ...extra,
})

describe('star rule (Constitution I)', () => {
  it('only server-confirmed states earn a star', () => {
    const all: UiState[] = ['unsolved', 'solving', 'tests_passed', 'submitted', 'verified', 'previously_completed', 'failed', 'blocked', 'skipped']
    expect(all.filter(hasStar)).toEqual(['verified', 'previously_completed'])
  })
})

describe('Calendar', () => {
  it('renders 25 days with independent part states', () => {
    const days: DayInfo[] = [
      { day: 1, title: 'Alpha', parts: { '1': part('verified'), '2': part('submitted') } },
      { day: 2, title: 'Beta', parts: { '1': part('tests_passed'), '2': part('blocked', { status_reason: 'Part 1 failed' }) } },
      { day: 3, title: null, parts: { '1': part('failed'), '2': part('unsolved') } },
    ]
    render(<Calendar days={days} dayFrom={1} dayTo={25} lastStar={null} currentDay={2} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(25)
    expect(screen.getByLabelText('Day 1 part 1: Verified by Advent of Code')).toBeInTheDocument()
    expect(screen.getByLabelText('Day 1 part 2: Submitted')).toBeInTheDocument()
    expect(screen.getByLabelText('Day 2 part 1: Tests passed')).toBeInTheDocument()
    expect(screen.getByLabelText('Day 2 part 2: Blocked — Part 1 failed')).toBeInTheDocument()
    expect(screen.getByLabelText('Day 3 part 1: Failed')).toBeInTheDocument()
  })
})

describe('ActivityFeed', () => {
  it('shows real event messages grouped by day/part and hides verbose types', () => {
    const events = [
      ev(1, 'agent.step', 'Loading puzzle…'),
      ev(2, 'part.state', 'NOT_STARTED → FETCHING'),
      ev(3, 'test.result', 'Test failed: expected 4, received 3', { level: 'error' }),
      ev(4, 'submit.result', 'Advent of Code accepted the answer', { level: 'success' }),
    ]
    render(<ActivityFeed events={events} />)
    expect(screen.getByText('Day 02 - Part 1')).toBeInTheDocument()
    expect(screen.getByText('Test failed: expected 4, received 3')).toBeInTheDocument()
    expect(screen.getByText('Advent of Code accepted the answer')).toBeInTheDocument()
    expect(screen.queryByText('NOT_STARTED → FETCHING')).not.toBeInTheDocument()
  })
})

describe('Escalation and replay banners', () => {
  it('shows the model switch with reason for the current part', () => {
    const events = [ev(9, 'agent.escalation', 'x', { data: { from_model: 'GPT-6.1 Sol', to_model: 'Claude Opus 5.5', reason: '3 unsuccessful attempts' } })]
    const e = latestEscalation(events, 2, 1)
    render(<EscalationBanner event={e} />)
    expect(screen.getByText('GPT-6.1 Sol')).toBeInTheDocument()
    expect(screen.getByText('Claude Opus 5.5')).toBeInTheDocument()
    expect(screen.getByText(/3 unsuccessful attempts/)).toBeInTheDocument()
    expect(latestEscalation(events, 3, 1)).toBeNull()
  })

  it('labels replay runs and never live runs', () => {
    const base = { id: 2, mode: 'replay', source_run_id: 1 } as Run
    const { rerender } = render(<ReplayBanner run={base} />)
    expect(screen.getByRole('alert')).toHaveTextContent('REPLAY of recorded run #1')
    rerender(<ReplayBanner run={{ ...base, mode: 'live' }} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
