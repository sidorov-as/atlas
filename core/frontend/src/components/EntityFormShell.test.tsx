// @vitest-environment jsdom
import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EntityFormShell, type MetadataDraft } from './EntityFormShell'

vi.mock('./DocumentationEditor', () => ({ DocumentationEditor: () => <div data-testid="documentation-editor" /> }))

afterEach(cleanup)

function ControlledShell({ onSubmit, layout }: { onSubmit: () => Promise<void>, layout?: 'single' | 'tabbed' }) {
  const [metadata, setMetadata] = useState<MetadataDraft>({ name: '', title: '', description: '', documentation: '', tags: '' })
  return (
    <EntityFormShell
      breadcrumb={{ label: 'Systems', to: '/systems' }}
      title="Add System"
      isEdit={false}
      metadata={metadata}
      onMetadataChange={setMetadata}
      specFields={null}
      onSubmit={onSubmit}
      cancelTo="/systems"
      layout={layout}
    />
  )
}

function renderShell(onSubmit: () => Promise<void>, layout?: 'single' | 'tabbed') {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <ControlledShell onSubmit={onSubmit} layout={layout} />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EntityFormShell Name field validation', () => {
  it('does not call onSubmit when Name is left blank and submit is triggered, and shows an inline error', () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    renderShell(onSubmit)
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Name is required')).toBeDefined()
  })

  it('clears the inline error once a Name is entered', () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    renderShell(onSubmit)
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(screen.getByText('Name is required')).toBeDefined()
    fireEvent.change(screen.getByPlaceholderText('my-system'), { target: { value: 'checkout' } })
    expect(screen.queryByText('Name is required')).toBeNull()
  })
})

describe('EntityFormShell header layout', () => {
  it('renders Save/Cancel in a header row above the fields, title on the left', () => {
    renderShell(vi.fn().mockResolvedValue(undefined))
    const title = screen.getByText('Add System', { selector: '.g-text_variant_header-1' })
    const saveButton = screen.getByRole('button', { name: 'Create' })
    const cancelButton = screen.getByRole('button', { name: 'Cancel' })
    const nameField = screen.getByPlaceholderText('my-system')

    // Header content (title, Save, Cancel) precedes the form body (Name field) in document order.
    expect(title.compareDocumentPosition(saveButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(title.compareDocumentPosition(cancelButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(saveButton.compareDocumentPosition(nameField) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('keeps Save as a submit button inside the form so Enter-to-submit still works', () => {
    renderShell(vi.fn().mockResolvedValue(undefined))
    expect(screen.getByRole('button', { name: 'Create' }).getAttribute('type')).toBe('submit')
  })
})

describe('EntityFormShell layout="single"', () => {
  it('renders fields and Documentation in one column with no tabs', () => {
    renderShell(vi.fn().mockResolvedValue(undefined), 'single')
    expect(screen.queryByRole('tab')).toBeNull()
    expect(screen.getByPlaceholderText('my-system')).toBeDefined()
    expect(screen.getByText('Documentation')).toBeDefined()
  })
})

describe('EntityFormShell layout="tabbed"', () => {
  it('splits fields into an Overview tab and Documentation into its own tab', () => {
    renderShell(vi.fn().mockResolvedValue(undefined), 'tabbed')
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined()
    expect(screen.getByRole('tab', { name: 'Documentation' })).toBeDefined()
    // Overview is the initial tab: Name is visible, the Documentation editor is not yet mounted.
    expect(screen.getByPlaceholderText('my-system')).toBeDefined()
    expect(screen.queryByTestId('documentation-editor')).toBeNull()
  })

  it('switches to the Documentation tab on click and shows the editor', () => {
    renderShell(vi.fn().mockResolvedValue(undefined), 'tabbed')
    fireEvent.click(screen.getByRole('tab', { name: 'Documentation' }))
    expect(screen.queryByPlaceholderText('my-system')).toBeNull()
    expect(screen.getByTestId('documentation-editor')).toBeDefined()
  })

  it('switches back to Overview when Name is empty on submit, so the inline error is visible', () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    renderShell(onSubmit, 'tabbed')
    fireEvent.click(screen.getByRole('tab', { name: 'Documentation' }))
    expect(screen.queryByPlaceholderText('my-system')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Create' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByPlaceholderText('my-system')).toBeDefined()
    expect(screen.getByText('Name is required')).toBeDefined()
  })
})
