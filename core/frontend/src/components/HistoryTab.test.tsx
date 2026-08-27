// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it } from 'vitest'
import { HistoryTab } from './HistoryTab'
import type { HistoryRecord } from '../lib/types'

afterEach(() => cleanup())

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = ResizeObserverStub

function renderTab(fetchHistory: () => Promise<HistoryRecord[]>) {
  return render(
    <ThemeProvider theme="light">
      <HistoryTab fetchHistory={fetchHistory} />
    </ThemeProvider>,
  )
}

describe('HistoryTab', () => {
  it('renders a remove-then-revive sequence with each action, actor, and timestamp, newest first', async () => {
    const records: HistoryRecord[] = [
      { action: 'revive', actor: 'Jane Doe', timestamp: '2026-02-02T00:00:00Z' },
      { action: 'remove', actor: 'Jane Doe', timestamp: '2026-01-01T00:00:00Z' },
    ]
    renderTab(async () => records)

    await waitFor(() => expect(screen.getByText('Revived')).toBeDefined())
    expect(screen.getByText('Removed')).toBeDefined()
    const actorCells = screen.getAllByText('Jane Doe')
    expect(actorCells).toHaveLength(2)

    const table = screen.getByRole('table')
    const rowTexts = Array.from(table.querySelectorAll('tbody tr')).map((row) => row.textContent)
    expect(rowTexts[0]).toContain('Revived')
    expect(rowTexts[1]).toContain('Removed')
  })

  it('shows "Ingestion" for a record with no actor', async () => {
    renderTab(async () => [{ action: 'remove', actor: null, timestamp: '2026-01-01T00:00:00Z' }])

    await waitFor(() => expect(screen.getByText('Removed')).toBeDefined())
    expect(screen.getByText('Ingestion')).toBeDefined()
  })

  it('shows an empty message when there is no history yet', async () => {
    renderTab(async () => [])

    await waitFor(() => expect(screen.getByText('No history yet')).toBeDefined())
  })
})
