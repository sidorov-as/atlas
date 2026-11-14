// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { GraphZoomToolbar } from './GraphZoomToolbar'

const camera = vi.hoisted(() => ({ zoomIn: vi.fn(), zoomOut: vi.fn(), fitView: vi.fn() }))
vi.mock('@xyflow/react', () => ({ useReactFlow: () => camera }))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

it('drives the canvas camera from the zoom, fit and zoom-out buttons', () => {
  render(<GraphZoomToolbar />)

  fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }))
  fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }))
  fireEvent.click(screen.getByRole('button', { name: 'Fit to viewport' }))

  expect(camera.zoomIn).toHaveBeenCalledTimes(1)
  expect(camera.zoomOut).toHaveBeenCalledTimes(1)
  expect(camera.fitView).toHaveBeenCalledWith({ duration: 200, padding: 0.2 })
})
