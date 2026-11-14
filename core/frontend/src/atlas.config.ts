// Deployment identity, hand-authored and committed.
// EventCatalog-style: editing this file and rebuilding is the only way to
// change a deployment's title/tagline/logo/icon — no backend endpoint, env
// var, or database record backs it.

export interface AtlasConfig {
  title: string
  tagline: string
  /** Path to the sidebar logo, served from `public/` (e.g. `/atlas-logo.svg`). */
  logo: string
  /** Optional sidebar logo for the dark theme, served from `public/`; the light `logo` is used when omitted. */
  logoDark?: string
  /** Path to the browser tab favicon, served from `public/`. */
  icon: string
}

export const atlasConfig: AtlasConfig = {
  title: 'Atlas',
  tagline: 'A software catalog for teams, systems, components, resources, and APIs.',
  logo: '/atlas-logo.svg',
  logoDark: '/atlas-logo-dark.svg',
  icon: '/favicon.ico',
}

/** The sidebar logo for the resolved theme: `logoDark` in dark when set, otherwise `logo`. */
export function logoForTheme(config: AtlasConfig, theme: 'light' | 'dark'): string {
  return theme === 'dark' ? (config.logoDark ?? config.logo) : config.logo
}
