// Plugin configuration contract (`plugin-configuration-isolation` spec, docs/plugin-architecture.md:475-491).
// The backend half is `atlas_plugin_api.config.PluginConfigSchema` (Pydantic) — this is its matching
// TypeScript half: only the *public projection* a plugin's backend explicitly opts into
// (`PluginConfigSchema.PUBLIC_FIELDS`) ever reaches the frontend, never the full config object and never
// a secret value, so this type is intentionally a plain JSON shape with no way to express a secret field.

/** A JSON-serializable value — the only shape a public config projection field may hold. */
export type PublicConfigValue =
  | string
  | number
  | boolean
  | null
  | readonly PublicConfigValue[]
  | { readonly [key: string]: PublicConfigValue }

/** One plugin's public configuration projection, keyed by the field names its backend declared safe to expose. */
export type PluginPublicConfig = Readonly<Record<string, PublicConfigValue>>

/** The public bootstrap configuration response: every installed plugin's public projection, keyed by plugin id. */
export type BootstrapConfig = Readonly<Record<string, PluginPublicConfig>>
