// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import DocumentationPreviewView from './DocumentationPreviewView'

describe('DocumentationPreview', () => {
  it('renders YFM notes and tabs with Diplodoc markup', () => {
    const { container } = render(
      <DocumentationPreviewView
        value={'{% note info "Demo guidance" %}\n\nUse the runbook.\n\n{% endnote %}\n\n{% list tabs %}\n\n- Happy path\n\n  Everything is healthy.\n\n{% endlist %}'}
      />,
    )

    expect(screen.getByText('Demo guidance')).toBeDefined()
    expect(screen.getByText('Happy path')).toBeDefined()
    expect(container.querySelector('.yfm-note')).not.toBeNull()
    expect(container.querySelector('.yfm-tabs')).not.toBeNull()
  })

  it('renders plain Markdown constructs (headings, lists, links) unchanged', () => {
    const { container } = render(
      <DocumentationPreviewView
        value={'# Heading\n\nSome **bold** text with a [link](https://example.com).\n\n- one\n- two\n'}
      />,
    )

    expect(container.querySelector('h1')?.textContent).toContain('Heading')
    expect(container.querySelector('strong')?.textContent).toBe('bold')
    const link = container.querySelector('a[href="https://example.com"]')
    expect(link?.textContent).toBe('link')
    expect(container.querySelectorAll('ul li')).toHaveLength(2)
  })
})
