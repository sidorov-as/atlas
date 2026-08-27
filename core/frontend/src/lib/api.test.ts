// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, onWriteDenied } from './api'

function mockFetch(status: number) {
  return vi.fn().mockResolvedValue(new Response(null, { status }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('onWriteDenied', () => {
  it('notifies listeners when an unsafe request comes back 403', async () => {
    vi.stubGlobal('fetch', mockFetch(403))
    const listener = vi.fn()
    onWriteDenied(listener)

    await apiFetch('/api/things/1/', { method: 'DELETE' })

    expect(listener).toHaveBeenCalledOnce()
  })

  it('does not notify for a 403 on a safe (GET) request', async () => {
    vi.stubGlobal('fetch', mockFetch(403))
    const listener = vi.fn()
    onWriteDenied(listener)

    await apiFetch('/api/things/1/')

    expect(listener).not.toHaveBeenCalled()
  })

  it('does not notify for a successful unsafe request', async () => {
    vi.stubGlobal('fetch', mockFetch(200))
    const listener = vi.fn()
    onWriteDenied(listener)

    await apiFetch('/api/things/1/', { method: 'POST' })

    expect(listener).not.toHaveBeenCalled()
  })

  it('stops notifying after unsubscribing', async () => {
    vi.stubGlobal('fetch', mockFetch(403))
    const listener = vi.fn()
    const unsubscribe = onWriteDenied(listener)
    unsubscribe()

    await apiFetch('/api/things/1/', { method: 'DELETE' })

    expect(listener).not.toHaveBeenCalled()
  })
})
