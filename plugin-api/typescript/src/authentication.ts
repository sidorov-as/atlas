/** Safe browser-authentication contracts matching `atlas.auth.providers.v1`. */

export type AuthenticationProviderId = string
export type AuthenticationProviderContractVersion = 'atlas.auth.providers.v1'
export type AuthenticationFlowKind = 'credentials' | 'redirect'
export type RemoteLogoutCapability = 'unsupported' | 'supported'
export type CredentialFieldKind = 'text' | 'secret'

export interface CredentialFieldPresentation {
  readonly id: string
  readonly label: string
  readonly kind: CredentialFieldKind
  readonly autocomplete?: string
}

/** Presentation-only metadata. It cannot represent provider connection data or secrets. */
export interface AuthenticationProviderPresentation {
  readonly displayName: string
  readonly credentialFields?: readonly CredentialFieldPresentation[]
}

/** One selected provider in Core's public login bootstrap response. */
export interface AuthenticationProviderBootstrap {
  readonly id: AuthenticationProviderId
  readonly contractVersion: AuthenticationProviderContractVersion
  readonly flowKind: AuthenticationFlowKind
  readonly presentation: AuthenticationProviderPresentation
  readonly remoteLogout: RemoteLogoutCapability
  readonly isDefault: boolean
  readonly signupOpen?: boolean
}

/** Entire frontend-safe authentication selection returned by Authentication Core. */
export interface AuthenticationBootstrapConfig {
  readonly providers: readonly AuthenticationProviderBootstrap[]
  readonly defaultProviderId: AuthenticationProviderId
  readonly providerChoiceUrl: string
}
