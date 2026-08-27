import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useSearchParams } from 'react-router-dom'
import { Alert, Button, Loader, PasswordInput, Text, TextInput } from '@gravity-ui/uikit'
import type { AuthenticationBootstrapConfig, AuthenticationProviderBootstrap } from '@atlas/plugin-api'
import {
  authenticationErrorMessage,
  getAuthenticationBootstrap,
  startRedirect,
} from '../lib/auth'
import { useSession } from '../lib/SessionContext'

const DEFAULT_RETURN_PATH = '/'
/**
 * Set synchronously by the logout handler, before any awaited request, so this
 * survives regardless of which navigation (RequireSession's automatic redirect
 * to bare `/login`, or an explicit one) reaches the router first — a plain
 * `?choose-provider=1` query param is not reliable here because both
 * navigations race and either can win.
 */
export const SKIP_AUTO_START_KEY = 'atlas.auth.skipAutoStartOnce'

function safeRelativePath(value: unknown): string {
  if (
    typeof value !== 'string'
    || !value.startsWith('/')
    || value.startsWith('//')
    || value.includes('\\')
    || Array.from(value).some((character) => character.charCodeAt(0) < 32)
  ) return DEFAULT_RETURN_PATH
  return value
}

function safeReturnPath(from: unknown): string {
  if (!from || typeof from !== 'object') return DEFAULT_RETURN_PATH
  const location = from as { pathname?: unknown; search?: unknown; hash?: unknown }
  if (
    typeof location.pathname !== 'string'
    || !location.pathname.startsWith('/')
    || location.pathname.startsWith('//')
  ) return DEFAULT_RETURN_PATH
  const search = typeof location.search === 'string' && location.search.startsWith('?') ? location.search : ''
  const hash = typeof location.hash === 'string' && location.hash.startsWith('#') ? location.hash : ''
  return safeRelativePath(`${location.pathname}${search}${hash}`)
}

function credentialProviders(config: AuthenticationBootstrapConfig | null) {
  return config?.providers.filter((provider) => provider.flowKind === 'credentials') ?? []
}

function initialCredentialProvider(config: AuthenticationBootstrapConfig): string | null {
  const defaultProvider = config.providers.find((provider) => provider.id === config.defaultProviderId)
  if (defaultProvider?.flowKind === 'credentials') return defaultProvider.id
  return credentialProviders(config)[0]?.id ?? null
}

export function LoginPage() {
  const { session, login } = useSession()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const stateReturnPath = safeReturnPath((location.state as { from?: unknown } | null)?.from)
  const queryReturnPath = searchParams.get('return-url')
  const returnPath = queryReturnPath === null ? stateReturnPath : safeRelativePath(queryReturnPath)
  const [config, setConfig] = useState<AuthenticationBootstrapConfig | null>(null)
  const [selectedCredentialProviderId, setSelectedCredentialProviderId] = useState<string | null>(null)
  const [credentials, setCredentials] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(
    searchParams.has('auth-error')
      ? authenticationErrorMessage(searchParams.get('auth-error'))
      : null,
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRedirecting, setIsRedirecting] = useState(false)
  const autoStartAttempted = useRef(false)
  const explicitChoice = searchParams.get('choose-provider') === '1' || searchParams.has('auth-error')

  useEffect(() => {
    getAuthenticationBootstrap()
      .then((bootstrap) => {
        setConfig(bootstrap)
        setSelectedCredentialProviderId(initialCredentialProvider(bootstrap))
      })
      .catch(() => setError('Authentication options could not be loaded. Please try again.'))
  }, [])

  const selectedCredentialProvider = useMemo(
    () => config?.providers.find((provider) => provider.id === selectedCredentialProviderId) ?? null,
    [config, selectedCredentialProviderId],
  )

  const redirect = useCallback(async (provider: AuthenticationProviderBootstrap) => {
    setError(null)
    setIsRedirecting(true)
    try {
      const redirectUrl = await startRedirect(provider.id, returnPath)
      window.location.assign(redirectUrl)
    } catch (err) {
      setError(err instanceof Error ? err.message : authenticationErrorMessage(null))
      setIsRedirecting(false)
    }
  }, [returnPath])

  useEffect(() => {
    if (!config || explicitChoice || session?.isAuthenticated || autoStartAttempted.current) return
    if (window.sessionStorage.getItem(SKIP_AUTO_START_KEY) === '1') {
      window.sessionStorage.removeItem(SKIP_AUTO_START_KEY)
      autoStartAttempted.current = true
      return
    }
    const defaultProvider = config.providers.find((provider) => provider.id === config.defaultProviderId)
    if (defaultProvider?.flowKind !== 'redirect') return
    autoStartAttempted.current = true
    void redirect(defaultProvider)
  }, [config, explicitChoice, redirect, session?.isAuthenticated])

  if (session?.isAuthenticated) return <Navigate to={returnPath} replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!selectedCredentialProvider) return
    setError(null)
    setIsSubmitting(true)
    try {
      await login(selectedCredentialProvider.id, credentials)
    } catch (err) {
      setError(err instanceof Error ? err.message : authenticationErrorMessage(null))
    } finally {
      setIsSubmitting(false)
    }
  }

  const redirectProviders = config?.providers.filter((provider) => provider.flowKind === 'redirect') ?? []
  const credentialsOptions = credentialProviders(config)
  const fields = selectedCredentialProvider?.presentation.credentialFields ?? []

  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 64 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, width: 360 }}>
        <Text variant="header-1">Atlas</Text>
        <Text color="secondary">Sign in to browse the catalog</Text>
        {error && <Alert theme="danger" message={error} />}
        {!config && !error && <Loader size="l" />}

        {config && credentialsOptions.length > 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {credentialsOptions.map((provider) => (
              <Button
                key={provider.id}
                type="button"
                view={provider.id === selectedCredentialProviderId ? 'action' : 'normal'}
                onClick={() => {
                  setSelectedCredentialProviderId(provider.id)
                  setCredentials({})
                }}
              >
                Use {provider.presentation.displayName}
              </Button>
            ))}
          </div>
        )}

        {selectedCredentialProvider && (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {fields.map((field, index) => (
              <label key={field.id} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <Text>{field.label}</Text>
                {field.kind === 'secret' ? (
                  <PasswordInput
                    size="l"
                    placeholder={field.label}
                    value={credentials[field.id] ?? ''}
                    onUpdate={(value) => setCredentials((current) => ({ ...current, [field.id]: value }))}
                    autoComplete={field.autocomplete}
                    autoFocus={index === 0}
                    disabled={isSubmitting || isRedirecting}
                    hideCopyButton
                  />
                ) : (
                  <TextInput
                    size="l"
                    placeholder={field.label}
                    value={credentials[field.id] ?? ''}
                    onUpdate={(value) => setCredentials((current) => ({ ...current, [field.id]: value }))}
                    autoComplete={field.autocomplete}
                    autoFocus={index === 0}
                    disabled={isSubmitting || isRedirecting}
                  />
                )}
              </label>
            ))}
            <Button
              view="action"
              size="l"
              type="submit"
              loading={isSubmitting}
              disabled={fields.length === 0 || fields.some((field) => !credentials[field.id]) || isRedirecting}
            >
              Sign in
            </Button>
          </form>
        )}

        {redirectProviders.length > 0 && selectedCredentialProvider && (
          <Text color="secondary" style={{ textAlign: 'center' }}>or</Text>
        )}
        {redirectProviders.map((provider) => (
          <Button
            key={provider.id}
            size="l"
            type="button"
            loading={isRedirecting && provider.id === config?.defaultProviderId}
            disabled={isSubmitting || isRedirecting}
            onClick={() => void redirect(provider)}
          >
            Sign in with {provider.presentation.displayName}
          </Button>
        ))}
        {config && config.providers.length === 0 && (
          <Alert theme="danger" message="No authentication providers are available." />
        )}
      </div>
    </div>
  )
}
