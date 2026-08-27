// Frontend optionality check for `atlas.apis` — no frontend plugin can otherwise learn
// whether another optional plugin is selected in the running distribution
// (`core/frontend/src/plugins/composition.ts` is composer-generated and
// only imported by core; `importBoundary.test.ts` forbids a plugin
// importing another's package). `FlowStepModal` calls this on mount to
// decide whether the Query/Event tiles render disabled.
//
// A conscious semantic reuse of `/healthz/plugins/` (`runtime-failure-
// isolation` spec, `server/health.py::PluginHealthView`), built for ops
// monitoring, not UI feature-detection — isolated behind this one helper so
// a future dedicated capability endpoint (if ever built) is a one-file swap.
import { apiFetch } from 'frontend/lib/api'

interface PluginHealthEntry {
  id: string
  status: string
}

interface PluginHealthResponse {
  plugins: PluginHealthEntry[]
}

const ATLAS_APIS_PLUGIN_ID = 'atlas.apis'

/**
 * `true` when `atlas.apis` is selected and reporting `active`. `/healthz/
 * plugins/` returns 503 when *any* selected plugin is degraded, so the
 * response body — not the HTTP status — is what's read here. Any fetch/
 * parse failure is treated as "unavailable" (fails closed): the Query/Event
 * tiles render disabled rather than risk offering an affordance that can't
 * actually save.
 */
export async function isAtlasApisAvailable(): Promise<boolean> {
  try {
    const response = await apiFetch('/healthz/plugins/')
    const body = (await response.json()) as PluginHealthResponse
    return body.plugins.some((plugin) => plugin.id === ATLAS_APIS_PLUGIN_ID && plugin.status === 'active')
  } catch {
    return false
  }
}
