// Resolves a Flow step's `entity_ref` against the catalog
// so callers can read the referenced entity's real subtype
// (`EntityNodeComponent`'s icon/color, Component/API/Data only) and its
// `title`/`description` off one shared fetch/cache. The latter now backs
// `EntityNodeComponent`'s client-side fallback for a step with no server-
// resolved `refStatus` yet — just added, or just re-pointed at a different
// reference, in the current edit session — not `FlowStepModal`'s Title/Summary prefill, which
// no longer exists for the six entity-backed kinds.
// `entity_ref` itself carries no subtype or description — it's a `kind:name`
// string — so this is a genuine fetch: `refName` (pure string parsing) is the
// only thing derivable from the ref with no network call behind it.
//
// `componentsApi`/`apisApi`/`groupsApi`/`resourcesApi`/`systemsApi`/`usersApi`
// (`frontend/lib/entities`) are core, not another plugin's package, so
// importing them here doesn't cross the boundary `importBoundary.test.ts`
// enforces (that only restricts a plugin importing another plugin's own
// package).
//
// `entity_ref` carries a `kind:name` pair, but each kind's `.get()` is keyed
// by the entity's UUID `id` (no name-based detail route exists), so a name
// can't be `.get()`-ed directly. Resolving a name goes through the *list*
// endpoint's `q` search param instead (`filter_by_search`'s
// `name__icontains`), reading `metadata.title`/`metadata.description` (and,
// for Component/API, `spec.type`) straight off the matching search-result
// item — no second `.get()` call needed. `q` is substring, not exact, so
// results are still filtered down to an exact (case-insensitive, matching
// `resolve_ref`'s own case-insensitivity) `metadata.name` match.
import { useEffect, useState } from 'react'
import { apisApi, componentsApi, groupsApi, resourcesApi, systemsApi, usersApi } from 'frontend/lib/entities'
import type { Paginated } from 'frontend/lib/types'

interface ResolvedEntityItem {
  metadata: { name: string; title: string; description: string }
  // Untyped on purpose: each of the six entity kinds' own `spec` shape is
  // unrelated (`UserSpec`, `SystemSpec`, ...), and only Component/API's carry
  // a `type` — a `{ type?: string }` field here would make TS's "weak type"
  // check reject every other kind's `spec` for sharing no property with it.
  spec?: unknown
}

/** One resolved `entity_ref`'s catalog data — `subtype` is `null` for every kind but Component/API/Data, which have no `spec.type` concept. */
export interface ResolvedEntityRef {
  title: string
  description: string
  subtype: string | null
}

/** Per-kind `q`-search-by-name lister, mirroring `RefSelect.tsx`'s `LISTERS` but narrowed server-side by `q` (that component instead lists everything once and filters/searches client-side in its own `Select`, which this fetch doesn't need). `usersApi.list()` returns a bare array unlike the other five kinds' `Paginated<T>` — handled by `listItems` below, mirroring `RefSelect.tsx`'s `useRefItems`. */
const LISTERS: Record<string, (name: string) => Promise<ResolvedEntityItem[] | Paginated<ResolvedEntityItem>>> = {
  user: (name) => usersApi.list({ q: name }),
  group: (name) => groupsApi.list({ q: name, pageSize: 100 }),
  component: (name) => componentsApi.list({ q: name, pageSize: 100 }),
  resource: (name) => resourcesApi.list({ q: name, pageSize: 100 }),
  api: (name) => apisApi.list({ q: name, pageSize: 100 }),
  system: (name) => systemsApi.list({ q: name, pageSize: 100 }),
}

function listItems(data: ResolvedEntityItem[] | Paginated<ResolvedEntityItem>): ResolvedEntityItem[] {
  return Array.isArray(data) ? data : data.page.objectList
}

/** Module-level cache, keyed by `entity_ref` — a Flow canvas/modal can reference the same catalog entity from several places, and this avoids a duplicate fetch per caller. `null` means "resolved, but no match" (fetch failed or ref didn't resolve); absent means "not yet fetched". */
const detailsCache = new Map<string, ResolvedEntityRef | null>()
const inFlight = new Map<string, Promise<ResolvedEntityRef | null>>()

async function fetchDetails(entityRef: string): Promise<ResolvedEntityRef | null> {
  const separator = entityRef.indexOf(':')
  if (separator === -1) return null
  const prefix = entityRef.slice(0, separator)
  const name = entityRef.slice(separator + 1)
  const lister = LISTERS[prefix]
  if (!lister) return null
  try {
    const match = listItems(await lister(name)).find((item) => item.metadata.name.toLowerCase() === name.toLowerCase())
    if (!match) return null
    return {
      title: match.metadata.title,
      description: match.metadata.description,
      subtype: (match.spec as { type?: string } | undefined)?.type ?? null,
    }
  } catch {
    return null
  }
}

/** Cache-and-dedupe wrapper shared by the reactive hook below and `fetchEntityRefDetails`'s imperative, one-shot use (`FlowStepModal`'s prefill-on-selection) — a ref already resolved elsewhere (e.g. a canvas node's own `useEntitySubtype`) is never re-fetched. */
function loadDetails(entityRef: string): Promise<ResolvedEntityRef | null> {
  if (detailsCache.has(entityRef)) return Promise.resolve(detailsCache.get(entityRef) ?? null)
  let promise = inFlight.get(entityRef)
  if (!promise) {
    promise = fetchDetails(entityRef).then((result) => {
      detailsCache.set(entityRef, result)
      inFlight.delete(entityRef)
      return result
    })
    inFlight.set(entityRef, promise)
  }
  return promise
}

/**
 * Imperative, one-shot resolution of `entityRef`'s `title`/`description` —
 * unlike `useEntityRefDetails`, this is not tied to a component's render and
 * fires exactly once per call, meant for a discrete "the author just picked
 * this" moment (`FlowStepModal`'s reference `onChange` handlers) rather than
 * a reactively-rendered value. Shares `useEntityRefDetails`'s cache, so
 * picking a reference already resolved elsewhere resolves instantly.
 */
export function fetchEntityRefDetails(entityRef: string): Promise<{ title: string, description: string } | null> {
  return loadDetails(entityRef).then((result) => (result ? { title: result.title, description: result.description } : null))
}

function resolve(entityRef: string, onResolved: (details: ResolvedEntityRef | null) => void): () => void {
  let cancelled = false
  loadDetails(entityRef).then((result) => {
    if (!cancelled) onResolved(result)
  })
  return () => { cancelled = true }
}

function useResolvedEntityRef(entityRef: string | null | undefined): ResolvedEntityRef | undefined {
  const [details, setDetails] = useState<ResolvedEntityRef | undefined>(() => {
    if (!entityRef) return undefined
    const cached = detailsCache.get(entityRef)
    return cached ?? undefined
  })

  useEffect(() => {
    if (!entityRef) {
      setDetails(undefined)
      return
    }
    if (detailsCache.has(entityRef)) {
      setDetails(detailsCache.get(entityRef) ?? undefined)
      return
    }
    setDetails(undefined)
    return resolve(entityRef, (result) => setDetails(result ?? undefined))
  }, [entityRef])

  return details
}

/**
 * The resolved Component/API/Data `type` for `entityRef` (e.g. `worker`,
 * `grpc`, `bucket`) — `undefined` while unresolved (not yet fetched, still
 * loading, or the fetch failed), so callers fall back to a neutral default
 * rather than guessing. Pass `undefined` for a
 * non-Component/API/Data kind or an unset ref to skip fetching entirely.
 */
export function useEntitySubtype(entityRef: string | null | undefined): string | undefined {
  return useResolvedEntityRef(entityRef)?.subtype ?? undefined
}

/**
 * The resolved entity's `title`/`description` for `entityRef`, across all
 * six entity-backed kinds — `undefined` while unresolved (not yet fetched,
 * still loading, the fetch failed, or `entityRef` is unset). Backs
 * `EntityNodeComponent`'s client-side fallback for a step with no
 * server-resolved `refStatus` entry yet — never used to write into the step itself.
 */
export function useEntityRefDetails(entityRef: string | null | undefined): { title: string, description: string } | undefined {
  const details = useResolvedEntityRef(entityRef)
  return details ? { title: details.title, description: details.description } : undefined
}
