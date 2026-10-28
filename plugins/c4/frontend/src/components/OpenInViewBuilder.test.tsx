// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { OpenInViewBuilder } from './OpenInViewBuilder'

afterEach(() => cleanup())

function Probe() {
  const location = useLocation()
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>
}

describe('OpenInViewBuilder', () => {
  it('links to the new view editor with the entity as root', () => {
    const id = '11111111-1111-4111-8111-111111111111'
    render(
      <MemoryRouter initialEntries={['/systems/x']}>
        <ThemeProvider theme="light"><OpenInViewBuilder entityId={id} /><Probe /></ThemeProvider>
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Open in view builder' }))
    expect(screen.getByTestId('location').textContent).toBe(`/system-map/views/new?root=${id}`)
  })
})
