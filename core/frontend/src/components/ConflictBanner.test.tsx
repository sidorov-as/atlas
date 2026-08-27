// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ConflictBanner } from './ConflictBanner'

afterEach(() => cleanup())

describe('ConflictBanner', () => {
  it('shows the adopt-to-resolve message for a manual_entity/other_repository conflict', () => {
    render(<ConflictBanner blockedBy="org/repo" reason="other_repository" />)
    expect(screen.getByText(/blocking a claim from `org\/repo`/)).toBeDefined()
    expect(screen.getByText(/adopt it to resolve the conflict/)).toBeDefined()
  })

  it('shows the revive-or-purge message for a removed_entity conflict', () => {
    render(<ConflictBanner blockedBy="org/repo" reason="removed_entity" />)
    expect(screen.getByText(/blocking a claim from `org\/repo`/)).toBeDefined()
    expect(screen.getByText(/an owner must revive or purge it/)).toBeDefined()
  })

  it('falls back to the adopt-to-resolve message when no reason is given', () => {
    render(<ConflictBanner blockedBy="org/repo" />)
    expect(screen.getByText(/adopt it to resolve the conflict/)).toBeDefined()
  })
})
