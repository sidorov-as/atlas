// @vitest-environment jsdom
import { act } from 'react'
import { ToasterProvider } from '@gravity-ui/uikit'
import { toaster } from '@gravity-ui/uikit/toaster-singleton'
import { render, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DocumentationEditorView from './DocumentationEditorView'

// Smoke test for the `uuid` workspace override (11.0.5 -> 11.1.1, GHSA-w5hq-g745-h8pq):
// @gravity-ui/markdown-editor was built and tested against the exact pinned 11.0.5,
// so this confirms the editor still mounts, generates block/mark IDs, and round-trips
// content through the overridden uuid version.
describe('DocumentationEditorView', () => {
  it('mounts the rich Markdown editor and round-trips content changes', async () => {
    const onChange = vi.fn()

    let container!: HTMLElement
    await act(async () => {
      ;({ container } = render(
        <ToasterProvider toaster={toaster}>
          <DocumentationEditorView value={'# Hello'} onChange={onChange} />
        </ToasterProvider>,
      ))
    })

    await waitFor(() => {
      expect(container.querySelector('[contenteditable="true"]')).not.toBeNull()
    })

    const editable = container.querySelector('[contenteditable="true"]') as HTMLElement
    expect(editable.textContent).toContain('Hello')
  })
})
