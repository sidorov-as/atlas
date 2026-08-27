// Flow-editor-page-scoped entity catalog:
// fetches every `entity_ref`-backed kind's full list exactly once per Flow
// editor page visit, shared by every `FlowStepModal` mount on that page,
// instead of each mount independently fetching its own capped page via
// `RefSelect`/`useRefItems`. `RefSelect` and its other consumers (Flow's own
// "Home system" field, `RelationsTab`'s `TargetRefSelect`, other entity
// forms' owner/system fields) are untouched.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { apisApi, componentsApi, groupsApi, resourcesApi, systemsApi, usersApi, type ListFilters } from 'frontend/lib/entities'
import type { Paginated } from 'frontend/lib/types'
import type { RefKind } from 'frontend/components/RefSelect'

/** Just enough of a catalog entity's shape for the lookup's item row — every `entity_ref`-backed kind's real entity type (`ComponentEntity`, `UserEntity`, etc.) is a structural superset of this, same as `RefSelect`'s own `NamedEntity`. */
export interface FlowCatalogEntity {
  metadata: { name: string; title: string }
}

interface FlowEntityCatalogValue {
  itemsByKind: Record<RefKind, FlowCatalogEntity[]>
  isLoading: boolean
}

const EMPTY_ITEMS: Record<RefKind, FlowCatalogEntity[]> = {
  component: [],
  resource: [],
  api: [],
  system: [],
  group: [],
  user: [],
}

const FlowEntityCatalogContext = createContext<FlowEntityCatalogValue | null>(null)

/** Fetches every page of a `Paginated<T>` list endpoint — unlike `RefSelect`'s `useRefItems`, this never stops at a single capped page. Safe against runaway loops because every list endpoint reports its own `numPages`. */
async function fetchAllPages<T>(list: (filters: ListFilters) => Promise<Paginated<T>>): Promise<T[]> {
  const items: T[] = []
  let page = 1
  for (;;) {
    const result = await list({ page, pageSize: 100 })
    items.push(...result.page.objectList)
    if (page >= result.numPages) return items
    page += 1
  }
}

const KIND_FETCHERS: Record<RefKind, () => Promise<FlowCatalogEntity[]>> = {
  component: () => fetchAllPages(componentsApi.list),
  resource: () => fetchAllPages(resourcesApi.list),
  api: () => fetchAllPages(apisApi.list),
  system: () => fetchAllPages(systemsApi.list),
  group: () => fetchAllPages(groupsApi.list),
  // Unlike the other kinds, `usersApi.list` already returns every User in one unpaginated response.
  user: () => usersApi.list(),
}

const REF_KINDS = Object.keys(KIND_FETCHERS) as RefKind[]

/** Provided once in `FlowFormPage` (the common ancestor of both `FlowStepModal` mount points via its own instance and `FlowCanvasEditor`'s), so both mounts share one fetch per page visit. */
export function FlowEntityCatalogProvider({ children }: { children: ReactNode }) {
  const [itemsByKind, setItemsByKind] = useState<Record<RefKind, FlowCatalogEntity[]>>(EMPTY_ITEMS)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    Promise.all(REF_KINDS.map((kind) =>
      KIND_FETCHERS[kind]()
        .then((items) => [kind, items] as const)
        // One kind's fetch failing (e.g. a plugin not installed) shouldn't blank out the others.
        .catch(() => [kind, []] as const),
    )).then((entries) => {
      if (!cancelled) setItemsByKind(Object.fromEntries(entries) as Record<RefKind, FlowCatalogEntity[]>)
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => { cancelled = true }
  }, [])

  const value = useMemo(() => ({ itemsByKind, isLoading }), [itemsByKind, isLoading])

  return <FlowEntityCatalogContext.Provider value={value}>{children}</FlowEntityCatalogContext.Provider>
}

/** Reads the page-scoped entity catalog (the `entity_ref` lookup). */
export function useFlowEntityCatalog(): FlowEntityCatalogValue {
  const context = useContext(FlowEntityCatalogContext)
  if (!context) throw new Error('useFlowEntityCatalog must be used within a FlowEntityCatalogProvider')
  return context
}

/**
 * Same as `useFlowEntityCatalog`, but returns `null` instead of throwing when
 * rendered outside a `FlowEntityCatalogProvider` (the node-title
 * lookup) — `FlowNodes.tsx`'s `EntityNodeComponent` is also used by the
 * read-only Flow detail canvas (`FlowGraph.tsx`, via `FlowDetailPage.tsx`),
 * which has no `FlowStepModal` to share a fetch with and so never mounts the
 * provider; that view's node titles simply skip the catalog lookup and fall
 * through to the existing `clientDetails`/`refName` fallbacks.
 */
export function useFlowEntityCatalogOptional(): FlowEntityCatalogValue | null {
  return useContext(FlowEntityCatalogContext)
}

/**
 * Looks up a catalog entity by an `entity_ref` (`kind:name`) directly against
 * `itemsByKind`, without going through `FlowNodeKind` (the node-title
 * lookup) — an `entity_ref`'s own kind prefix already is a `RefKind`, the
 * same one `FlowStepModal`'s `entity_ref` field keys `itemsByKind`
 * by.
 */
export function findFlowCatalogEntity(itemsByKind: Record<RefKind, FlowCatalogEntity[]> | undefined, entityRef: string | null | undefined): FlowCatalogEntity | undefined {
  if (!itemsByKind || !entityRef) return undefined
  const separator = entityRef.indexOf(':')
  if (separator === -1) return undefined
  const kind = entityRef.slice(0, separator) as RefKind
  const name = entityRef.slice(separator + 1)
  return itemsByKind[kind]?.find((item) => item.metadata.name === name)
}
