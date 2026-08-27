// Atlas-owned browser authentication gateway.
import type { AuthenticationBootstrapConfig } from '@atlas/plugin-api'
import { apiFetch, apiJson } from './api'

const AUTH_BASE_URL = '/auth/browser/v1'
const SESSION_URL = `${AUTH_BASE_URL}/session`
const CONFIG_URL = `${AUTH_BASE_URL}/config`

export interface SessionUser {
  id: number
  display: string
  username: string
}

export interface SessionState {
  isAuthenticated: boolean
  user: SessionUser | null
  /** Authorization-role signal, kept separate from the authentication payload. */
  isAdmin: boolean
  /** Presentation signal only; backend authorization remains the write boundary. */
  isReadOnly: boolean
}

interface SessionBody {
  data?: { user?: SessionUser | null }
  meta?: { is_authenticated?: boolean }
}

interface AuthenticationErrorBody {
  error?: {
    category?: string
    stage?: string
    correlationId?: string
    retryable?: boolean
  }
}

interface MeResponse {
  isAdmin: boolean
  isReadOnly: boolean
}

export class AuthenticationError extends Error {
  readonly category: string
  readonly correlationId: string | null
  readonly retryable: boolean

  constructor(body: AuthenticationErrorBody | null) {
    const category = body?.error?.category ?? 'authentication_failed'
    super(authenticationErrorMessage(category))
    this.name = 'AuthenticationError'
    this.category = category
    this.correlationId = body?.error?.correlationId ?? null
    this.retryable = body?.error?.retryable ?? false
  }
}

/** Maps allowlisted gateway categories to stable UI copy without exposing provider details. */
export function authenticationErrorMessage(category: string | null): string {
  switch (category) {
    case 'canceled':
      return 'Sign-in was canceled. Choose a provider to try again.'
    case 'provider_unavailable':
      return 'That sign-in provider is temporarily unavailable. Choose another provider or try again.'
    case 'invalid_credentials':
      return 'The credentials were not accepted.'
    case 'provisioning_failed':
      return 'Your identity could not be provisioned for this deployment.'
    case 'invalid_state':
      return 'The sign-in attempt expired or was already used. Please try again.'
    default:
      return 'Sign-in failed. Choose a provider to try again.'
  }
}

async function getMe(): Promise<MeResponse> {
  return apiJson<MeResponse>('/api/me/')
}

async function toSessionState(response: Response): Promise<SessionState> {
  const body = (await response.json()) as SessionBody
  const isAuthenticated = Boolean(body.meta?.is_authenticated)
  const me = isAuthenticated ? await getMe() : { isAdmin: false, isReadOnly: false }
  return {
    isAuthenticated,
    user: body.data?.user ?? null,
    isAdmin: me.isAdmin,
    isReadOnly: me.isReadOnly,
  }
}

/** Reads the current Core-owned session and primes the CSRF cookie. */
export async function getSession(): Promise<SessionState> {
  return toSessionState(await apiFetch(SESSION_URL))
}

/** Loads only selected, frontend-safe provider presentation from Authentication Core. */
export async function getAuthenticationBootstrap(): Promise<AuthenticationBootstrapConfig> {
  return apiJson<AuthenticationBootstrapConfig>(CONFIG_URL)
}

/** Submits credentials to the selected provider-specific gateway operation. */
export async function login(
  providerId: string,
  credentials: Readonly<Record<string, string>>,
): Promise<SessionState> {
  const response = await apiFetch(
    `${AUTH_BASE_URL}/providers/${encodeURIComponent(providerId)}/credentials`,
    { method: 'POST', body: JSON.stringify({ credentials }) },
  )
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as AuthenticationErrorBody | null
    throw new AuthenticationError(body)
  }
  return toSessionState(response)
}

interface RedirectStartBody {
  redirectUrl: string
  correlationId: string
}

/** Starts a selected redirect provider and returns its validated authorization URL. */
export async function startRedirect(providerId: string, returnUrl: string): Promise<string> {
  const response = await apiFetch(
    `${AUTH_BASE_URL}/providers/${encodeURIComponent(providerId)}/start`,
    { method: 'POST', body: JSON.stringify({ returnUrl }) },
  )
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as AuthenticationErrorBody | null
    throw new AuthenticationError(body)
  }
  const body = (await response.json()) as RedirectStartBody
  return body.redirectUrl
}

export async function logout(): Promise<void> {
  await apiFetch(SESSION_URL, { method: 'DELETE' })
}
