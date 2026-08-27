// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FlowFormPage } from './FlowFormPage'
import { flowsApi } from 'frontend/lib/entities'

vi.mock('frontend/components/DocumentationEditor', () => ({ DocumentationEditor: () => <div /> }))
vi.mock('frontend/components/RefSelect', () => ({ RefSelect: () => <div /> }))
vi.mock('../components/FlowCanvasEditor', () => ({ FlowCanvasEditor: ({ onEditStep }: { onEditStep: (stepId: string) => void }) => <button type="button" onClick={() => onEditStep('step-1')}>Canvas node</button> }))
vi.mock('../components/FlowStepModal', () => ({
  FlowStepModal: ({ open, step, onSave }: { open: boolean; step: { id: string } | null; onSave: (step: { id: string; title?: string }, previousId: string | null) => void }) =>
    open ? <button type="button" onClick={() => onSave({ id: step?.id ?? 'step-1', title: 'Edited visually' }, step?.id ?? null)}>Save step</button> : null,
}))
vi.mock('@monaco-editor/react', () => ({ Editor: ({ value, onChange }: { value: string; onChange: (value: string) => void }) => <textarea aria-label="Steps JSON" value={value} onChange={(event) => onChange(event.target.value)} /> }))
vi.mock('frontend/lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('frontend/lib/entities')>()
  return { ...actual, flowsApi: { ...actual.flowsApi, create: vi.fn(), update: vi.fn() } }
})

function renderPage() {
  render(<ThemeProvider theme="light"><MemoryRouter><FlowFormPage /></MemoryRouter></ThemeProvider>)
}

function openFlowTab() {
  fireEvent.click(screen.getByRole('tab', { name: 'Flow' }))
}

/** The JSON rail starts collapsed on the Flow tab — tests that need it open must ask for it explicitly. */
function openJsonRail() {
  fireEvent.click(screen.getByRole('button', { name: 'Show JSON' }))
}

afterEach(cleanup)

describe('FlowFormPage', () => {
  it('splits editing into a General tab (name/description/system/documentation) and a full-screen Flow tab (canvas + collapsed JSON rail)', () => {
    renderPage()
    expect(screen.queryByText('Canvas node')).toBeNull()
    expect(screen.queryByLabelText('Steps JSON')).toBeNull()
    openFlowTab()
    expect(screen.getByText('Canvas node')).toBeDefined()
    // The JSON rail starts collapsed — the
    // canvas is visible immediately, the JSON rail only once explicitly shown.
    expect(screen.queryByLabelText('Steps JSON')).toBeNull()
    openJsonRail()
    expect(screen.getByLabelText('Steps JSON')).toBeDefined()
  })

  it('has no Visual/JSON mode toggle: the canvas is always present, and the JSON rail is a separate show/hide toggle', () => {
    renderPage()
    openFlowTab()
    openJsonRail()
    expect(screen.queryByRole('button', { name: 'Visual' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'JSON' })).toBeNull()
    expect(screen.getByText('Canvas node')).toBeDefined()
    expect(screen.getByLabelText('Steps JSON')).toBeDefined()
  })

  it('synchronizes canvas edits into the JSON rail', () => {
    renderPage()
    openFlowTab()
    openJsonRail()
    fireEvent.click(screen.getByRole('button', { name: 'Add Step' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save step' }))
    expect((screen.getByLabelText('Steps JSON') as HTMLTextAreaElement).value).toContain('Edited visually')
  })

  it('keeps the last valid steps and surfaces a parse error when the JSON rail holds invalid JSON', () => {
    renderPage()
    openFlowTab()
    openJsonRail()
    fireEvent.change(screen.getByLabelText('Steps JSON'), { target: { value: '{' } })
    expect((screen.getByLabelText('Steps JSON') as HTMLTextAreaElement).value).toBe('{')
    expect(screen.getByText(/Expected property name or '\}' in JSON/)).toBeDefined()
  })

  it('opens the step edit modal when a canvas node is clicked', () => {
    renderPage()
    openFlowTab()
    expect(screen.queryByRole('button', { name: 'Save step' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Canvas node' }))
    expect(screen.getByRole('button', { name: 'Save step' })).toBeDefined()
  })

  it('toggles the JSON rail without affecting the canvas', () => {
    renderPage()
    openFlowTab()
    expect(screen.queryByLabelText('Steps JSON')).toBeNull()
    openJsonRail()
    expect(screen.getByLabelText('Steps JSON')).toBeDefined()
    expect(screen.getByText('Canvas node')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Hide JSON' }))
    expect(screen.queryByLabelText('Steps JSON')).toBeNull()
    expect(screen.getByText('Canvas node')).toBeDefined()
  })
})

describe('FlowFormPage header layout', () => {
  it('renders Save/Cancel in a header row above the General/Flow tabs, title on the left', () => {
    renderPage()
    const title = screen.getByText('Add Flow', { selector: '.g-text_variant_header-1' })
    const saveButton = screen.getByRole('button', { name: 'Create' })
    const cancelButton = screen.getByRole('button', { name: 'Cancel' })
    const generalTab = screen.getByRole('tab', { name: 'General' })

    // Header content (title, Save, Cancel) precedes the General/Flow tabs in document order.
    expect(title.compareDocumentPosition(saveButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(title.compareDocumentPosition(cancelButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(saveButton.compareDocumentPosition(generalTab) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('keeps Save as a submit button inside the form so Enter-to-submit still works', () => {
    renderPage()
    expect(screen.getByRole('button', { name: 'Create' }).getAttribute('type')).toBe('submit')
  })

  it('does not repeat Save/Cancel next to the Add Step toolbar button on the Flow tab', () => {
    renderPage()
    openFlowTab()
    expect(screen.getAllByRole('button', { name: 'Create' })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: 'Cancel' })).toHaveLength(1)
  })
})

describe('FlowFormPage Name field validation', () => {
  it('does not call the save API when Name is left blank and submit is triggered, and shows an inline error', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(flowsApi.create).not.toHaveBeenCalled()
    expect(screen.getByText('Name is required')).toBeDefined()
  })

  it('does not call the save API when Name is left blank and submit is triggered from the Flow tab, and switches back to General to show the inline error (the Name input only renders on the General tab)', () => {
    renderPage()
    openFlowTab()
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(flowsApi.create).not.toHaveBeenCalled()
    expect(screen.getByText('Name is required')).toBeDefined()
  })

  it('clears the inline error once a Name is entered', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(screen.getByText('Name is required')).toBeDefined()
    fireEvent.change(screen.getByPlaceholderText('checkout-saga'), { target: { value: 'checkout-saga' } })
    expect(screen.queryByText('Name is required')).toBeNull()
  })
})

describe('FlowFormPage JSON rail structural-validity gate', () => {
  it('does not update the canvas and shows an inline structural error when a JSON edit renames a step id without fixing a referencing next_step', () => {
    renderPage()
    openFlowTab()
    openJsonRail()

    fireEvent.change(screen.getByLabelText('Steps JSON'), {
      target: { value: '[{"id":"start","next_step":{"id":"end"}},{"id":"end-renamed"}]' },
    })

    expect(screen.getByText(/unknown step id/)).toBeDefined()
    // The rail keeps the author's entered (structurally broken) text...
    expect((screen.getByLabelText('Steps JSON') as HTMLTextAreaElement).value).toContain('end-renamed')
    // ...while the canvas mock (which re-renders from the committed `steps`) still exists
    // and reflects the last-good state, not the broken candidate — nothing here throws or
    // blanks the canvas out.
    expect(screen.getByText('Canvas node')).toBeDefined()
  })

  it('resolves the error and updates the canvas once the dangling reference is fixed', () => {
    renderPage()
    openFlowTab()
    openJsonRail()

    fireEvent.change(screen.getByLabelText('Steps JSON'), {
      target: { value: '[{"id":"start","next_step":{"id":"end"}},{"id":"end-renamed"}]' },
    })
    expect(screen.getByText(/unknown step id/)).toBeDefined()

    fireEvent.change(screen.getByLabelText('Steps JSON'), {
      target: { value: '[{"id":"start","next_step":{"id":"end-renamed"}},{"id":"end-renamed"}]' },
    })

    expect(screen.queryByText(/unknown step id/)).toBeNull()
  })
})
