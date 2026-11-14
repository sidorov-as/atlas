// @vitest-environment jsdom
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DiagramViewer } from './DiagramTab'

class ResizeObserverStub {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}
globalThis.ResizeObserver = ResizeObserverStub

const fetchMock = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  let created = 0
  URL.createObjectURL = vi.fn(() => `blob:${++created}`)
  URL.revokeObjectURL = vi.fn()
})

afterEach(() => {
  cleanup()
  fetchMock.mockReset()
  vi.unstubAllGlobals()
})

function svg() {
  return new Response('<svg />', { status: 200, headers: { 'Content-Type': 'image/svg+xml' } })
}

function error(status: number, detail: object) {
  return new Response(JSON.stringify({ detail: [detail] }), { status, headers: { 'Content-Type': 'application/json' } })
}

const view = (src: string, props: Partial<React.ComponentProps<typeof DiagramViewer>> = {}) => (
  <ThemeProvider theme="light"><DiagramViewer src={src} alt="custom" fetchSource {...props} /></ThemeProvider>
)

describe('DiagramViewer fetch mode', () => {
  it('fetches the source and shows the result through an object URL', async () => {
    fetchMock.mockResolvedValueOnce(svg())
    const onFetchingChange = vi.fn()
    render(view('/api/a', { onFetchingChange }))
    const image = (await screen.findByAltText('custom')) as HTMLImageElement
    expect(image.src).toBe('blob:1')
    expect(onFetchingChange).toHaveBeenLastCalledWith(false)
  })

  it('keeps the previous image and reports a structured error when a later request fails', async () => {
    fetchMock.mockResolvedValueOnce(svg())
    const onFetchError = vi.fn()
    const { rerender } = render(view('/api/a', { onFetchError }))
    await screen.findByAltText('custom')
    fetchMock.mockResolvedValueOnce(error(422, { msg: 'too many', type: 'node_limit_exceeded', limit: 50, count: 72 }))
    rerender(view('/api/b', { onFetchError }))
    await waitFor(() => expect(onFetchError).toHaveBeenCalled())
    expect(onFetchError.mock.calls[0][0]).toMatchObject({ status: 422, code: 'node_limit_exceeded', limit: 50, count: 72 })
    expect((screen.getByAltText('custom') as HTMLImageElement).src).toBe('blob:1')
  })

  it('aborts a superseded request and ignores its response', async () => {
    let resolveFirst: (response: Response) => void = () => {}
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => { resolveFirst = resolve }))
    fetchMock.mockResolvedValueOnce(svg())
    const { rerender } = render(view('/api/a'))
    rerender(view('/api/b'))
    const image = (await screen.findByAltText('custom')) as HTMLImageElement
    await act(async () => { resolveFirst(svg()) })
    expect(image.src).toBe('blob:1')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:2')
    expect((fetchMock.mock.calls[0][1] as RequestInit).signal?.aborted).toBe(true)
  })

  it('refetches when the reload token changes', async () => {
    fetchMock.mockResolvedValue(svg())
    const { rerender } = render(view('/api/a', { reloadToken: 0 }))
    await screen.findByAltText('custom')
    rerender(view('/api/a', { reloadToken: 1 }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('posts the request body for a draft preview and refetches when it changes', async () => {
    fetchMock.mockResolvedValue(svg())
    const { rerender } = render(view('/api/preview', { requestBody: '{"a":1}' }))
    await screen.findByAltText('custom')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', body: '{"a":1}' })
    rerender(view('/api/preview', { requestBody: '{"a":2}' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST', body: '{"a":2}' })
  })

  it('ignores a stale preview response and keeps the previous image when a new body fails', async () => {
    fetchMock.mockResolvedValueOnce(svg())
    const onFetchError = vi.fn()
    const { rerender } = render(view('/api/preview', { requestBody: '1', onFetchError }))
    await screen.findByAltText('custom')
    fetchMock.mockResolvedValueOnce(error(404, { msg: 'gone', type: 'unknown_entity', entity: 'e1' }))
    rerender(view('/api/preview', { requestBody: '2', onFetchError }))
    await waitFor(() => expect(onFetchError).toHaveBeenCalled())
    expect(onFetchError.mock.calls[0][0]).toMatchObject({ code: 'unknown_entity', entity: 'e1' })
    expect((screen.getByAltText('custom') as HTMLImageElement).src).toBe('blob:1')
  })
})
