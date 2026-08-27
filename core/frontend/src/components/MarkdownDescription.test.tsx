// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarkdownDescription } from './MarkdownDescription'

describe('MarkdownDescription', () => {
  it('renders YFM note directives as a labeled info callout', () => {
    render(<MarkdownDescription text={'{% note info %}\n\nkek\n\n{% endnote %}'} />)

    expect(screen.getByText('Info')).toBeDefined()
    expect(screen.getByText('kek').closest('.markdown-note--info')).not.toBeNull()
    expect(screen.queryByText('{% note info %}')).toBeNull()
  })
})
