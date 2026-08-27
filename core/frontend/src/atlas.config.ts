// Deployment identity, hand-authored and committed.
// EventCatalog-style: editing this file and rebuilding is the only way to
// change a deployment's title/tagline/logo/icon — no backend endpoint, env
// var, or database record backs it.

export interface AtlasConfig {
  title: string
  tagline: string
  /** Path to the sidebar logo, served from `public/` (e.g. `/atlas-logo.svg`). */
  logo: string
  /** Path to the browser tab favicon, served from `public/`. */
  icon: string
}

export const atlasConfig: AtlasConfig = {
  title: 'Atlas',
  tagline: 'A software catalog for teams, systems, components, resources, and APIs.',
  logo: '/atlas-logo.svg',
  icon: '/favicon.ico',
}
