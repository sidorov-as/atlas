// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationMessageTab } from './OperationMessageTab'
import { makeOperation, makeOperationMessage } from '../testFixtures'

afterEach(() => cleanup())

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

const HEADERS_SCHEMA = {
  type: 'object' as const,
  '$ref': null,
  format: '',
  enum: null,
  nullable: false,
  description: '',
  properties: { correlationId: { type: 'string' as const, '$ref': null, format: '', enum: null, nullable: false, description: '', properties: {}, required: [], items: null } },
  required: [],
  items: null,
}

function renderTab(messages: Parameters<typeof makeOperationMessage>[0][]) {
  return render(
    <ThemeProvider theme="light">
      <OperationMessageTab operation={makeOperation({ messages: messages.map((overrides) => makeOperationMessage(overrides)) })} />
    </ThemeProvider>,
  )
}

describe('OperationMessageTab', () => {
  it('shows a Headers section when the message has a headers schema', () => {
    renderTab([{ headers: HEADERS_SCHEMA }])
    expect(screen.getByText('Headers')).toBeDefined()
    expect(screen.getByText('correlationId')).toBeDefined()
  })

  it('omits the Headers section when the message has no headers', () => {
    renderTab([{ headers: null }])
    expect(screen.queryByText('Headers')).toBeNull()
  })
})
