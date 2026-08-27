// @vitest-environment jsdom
import { useState } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it } from 'vitest'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { useConfirm, type ConfirmOptions } from './useConfirm'

afterEach(() => cleanup())

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = ResizeObserverStub

window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)

function Harness({ preset }: { preset?: ConfirmOptions['preset'] }) {
  const { confirm, dialogProps } = useConfirm()
  const [result, setResult] = useState('pending')

  async function trigger() {
    const confirmed = await confirm({ title: 'Remove item', message: 'Are you sure?', preset })
    setResult(confirmed ? 'confirmed' : 'cancelled')
  }

  return (
    <div>
      <button onClick={() => void trigger()}>Trigger</button>
      <div data-testid="result">{result}</div>
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}

function renderHarness(preset?: ConfirmOptions['preset']) {
  return render(
    <ThemeProvider theme="light">
      <Harness preset={preset} />
    </ThemeProvider>,
  )
}

describe('useConfirm / ConfirmDialog', () => {
  it('resolves true when the confirm control is clicked', async () => {
    renderHarness()
    fireEvent.click(screen.getByText('Trigger'))

    await waitFor(() => expect(screen.getByText('Are you sure?')).toBeDefined())
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => expect(screen.getByTestId('result').textContent).toBe('confirmed'))
    expect(screen.queryByText('Are you sure?')).toBeNull()
  })

  it('resolves false when the cancel control is clicked', async () => {
    renderHarness()
    fireEvent.click(screen.getByText('Trigger'))

    await waitFor(() => expect(screen.getByText('Are you sure?')).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.getByTestId('result').textContent).toBe('cancelled'))
  })

  it('resolves false when dismissed via Escape', async () => {
    renderHarness()
    fireEvent.click(screen.getByText('Trigger'))

    await waitFor(() => expect(screen.getByText('Are you sure?')).toBeDefined())
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

    await waitFor(() => expect(screen.getByTestId('result').textContent).toBe('cancelled'))
  })

  it('forwards the danger preset to Dialog.Footer', async () => {
    renderHarness('danger')
    fireEvent.click(screen.getByText('Trigger'))

    const applyButton = await screen.findByText('Confirm')
    await waitFor(() => expect(applyButton.closest('button')?.className).toMatch(/preset_danger/))
  })

  it('forwards the default preset to Dialog.Footer', async () => {
    renderHarness('default')
    fireEvent.click(screen.getByText('Trigger'))

    const applyButton = await screen.findByText('Confirm')
    await waitFor(() => expect(applyButton.closest('button')?.className).toMatch(/preset_default/))
    expect(applyButton.closest('button')?.className).not.toMatch(/preset_danger/)
  })
})
