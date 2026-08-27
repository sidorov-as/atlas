// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiFormPage } from './ApiFormPage'

afterEach(() => cleanup())

vi.mock('frontend/components/RefSelect', () => ({ RefSelect: () => <div /> }))

vi.mock('frontend/lib/entities', () => ({
  apisApi: { get: vi.fn(), create: vi.fn(), update: vi.fn() },
}))

// Same pattern as SchemaEditorTab.test.tsx/FlowFormPage.test.tsx: stub Monaco's `Editor` with a
// plain textarea, exposing the resolved `language` prop so tests can assert the auto-detected
// JSON/YAML highlighting without a real Monaco mount in jsdom.
vi.mock('@monaco-editor/react', () => ({
  Editor: ({ value, onChange, language }: { value: string, onChange: (value: string) => void, language: string }) => (
    <div>
      <div data-testid="spec-editor-language">{language}</div>
      <textarea aria-label="Spec content" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  ),
}))

function renderPage() {
  render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <ApiFormPage />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

function openInlineSpecEditor() {
  fireEvent.click(screen.getByText('Paste text'))
}

describe('ApiFormPage inline spec editor', () => {
  it('highlights JSON-looking content as JSON', async () => {
    renderPage()
    openInlineSpecEditor()

    fireEvent.change(await screen.findByLabelText('Spec content'), { target: { value: '{"openapi": "3.0.0"}' } })
    expect(screen.getByTestId('spec-editor-language').textContent).toBe('json')
  })

  it('highlights non-JSON-looking content as YAML', async () => {
    renderPage()
    openInlineSpecEditor()

    fireEvent.change(await screen.findByLabelText('Spec content'), { target: { value: 'openapi: 3.0.0' } })
    expect(screen.getByTestId('spec-editor-language').textContent).toBe('yaml')
  })

  it('shows a visible inline error when the content fails to parse', async () => {
    renderPage()
    openInlineSpecEditor()

    fireEvent.change(await screen.findByLabelText('Spec content'), { target: { value: '{ broken' } })
    expect(screen.getByText(/unexpected end of the stream/)).toBeDefined()
  })

  it('shows no inline error when the content parses successfully', async () => {
    renderPage()
    openInlineSpecEditor()

    fireEvent.change(await screen.findByLabelText('Spec content'), { target: { value: 'openapi: 3.0.0' } })
    expect(screen.queryByText(/unexpected end of the stream/)).toBeNull()
  })
})
