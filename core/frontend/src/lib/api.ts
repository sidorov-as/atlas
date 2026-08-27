// Shared fetch wrapper for the SPA: same-origin session cookie + Django's
// CSRF double-submit cookie on state-changing requests (session-based auth,
// no JWT).

const CSRF_COOKIE_NAME = 'csrftoken'
const CSRF_HEADER_NAME = 'X-CSRFToken'
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

/** Reads Django's CSRF double-submit cookie, primed by an earlier `apiFetch` GET. */
export function readCsrfCookie(): string | null {
  return readCookie(CSRF_COOKIE_NAME)
}

export class ApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`)
    this.status = status
    this.body = body
  }
}

/**
 * Notified whenever an unsafe (write) request comes back 403, regardless of
 * which form/page issued it (a write-denied response is one of the
 * moments access state must refresh).
 * `SessionContext` is the only expected subscriber — it re-fetches
 * `/api/me/` so stale write affordances correct themselves — kept here
 * instead of scattered per call site since every write goes through
 * `apiFetch`.
 */
type WriteDeniedListener = () => void
const writeDeniedListeners = new Set<WriteDeniedListener>()

export function onWriteDenied(listener: WriteDeniedListener): () => void {
  writeDeniedListeners.add(listener)
  return () => writeDeniedListeners.delete(listener)
}

/** Fetches `path`, attaching the session cookie and, for unsafe methods, the CSRF header. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)

  if (!SAFE_METHODS.has(method)) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME)
    if (csrfToken) headers.set(CSRF_HEADER_NAME, csrfToken)
  }
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, { ...init, method, headers, credentials: 'same-origin' })
  if (response.status === 403 && !SAFE_METHODS.has(method)) {
    for (const listener of writeDeniedListeners) listener()
  }
  return response
}

/** Like `apiFetch`, but parses the JSON body and throws `ApiError` on a non-OK status. */
export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init)
  if (!response.ok) {
    let body: unknown = null
    try {
      body = await response.json()
    } catch {
      // No JSON body to report.
    }
    throw new ApiError(response.status, body)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Extracts a dmr-style `{ detail: [{ msg }] }` validation message from `err`, falling back to `err.message`. */
export function errorMessage(err: unknown, fallback = 'Request failed'): string {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: { msg?: string }[] } | null
    const detail = body?.detail?.map((item) => item.msg).filter(Boolean).join('; ')
    if (detail) return detail
  }
  return err instanceof Error ? err.message : fallback
}
