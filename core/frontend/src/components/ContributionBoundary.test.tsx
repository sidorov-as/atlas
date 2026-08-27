// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ContributionBoundary } from './ContributionBoundary'

afterEach(() => cleanup())

describe('ContributionBoundary', () => {
  it('renders its children when they do not throw', () => {
    render(
      <ContributionBoundary label="Widget">
        <div>Widget content</div>
      </ContributionBoundary>,
    )
    expect(screen.getByText('Widget content')).toBeDefined()
  })

  it('isolates a throwing child behind a labeled fallback instead of propagating the error', () => {
    function Broken(): never {
      throw new Error('boom')
    }
    render(
      <ContributionBoundary label="Widget">
        <Broken />
      </ContributionBoundary>,
    )
    expect(screen.getByText('Widget failed to load')).toBeDefined()
  })
})
