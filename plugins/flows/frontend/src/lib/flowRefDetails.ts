// Resolves a Flow step's `flow_ref` (another Flow's id) against the Flow API
// mirroring
// `entitySubtype.ts`'s `useEntityRefDetails` for `entity_ref` — but simpler,
// since `flow_ref` is already the target's id (no `kind:name` parse/search
// needed, unlike `entity_ref`) and a Flow has no removed/deprecated status of
// its own, only "exists" or "doesn't".
//
// Unlike `useEntityRefDetails` (which returns `T | undefined`, conflating
// "still loading" with "confirmed absent" — acceptable there since nothing
// reads that ambiguity), this hook's return distinguishes the two: `null`
// specifically means "the fetch settled and found nothing," used as a
// same-session confirmation signal alongside the server-computed `refStatus`
// for the stale-reference warning (`FlowNodes.tsx`) — a step referencing a
// real Flow the author just picked resolves via this fetch almost
// immediately, before the Flow is ever saved, so the warning doesn't have to
// wait for a save+reread to avoid a false positive on a brand-new step.
import { useEffect, useState } from 'react'
import { flowsApi } from 'frontend/lib/entities'

export interface ResolvedFlowRef {
  name: string
  description: string
}

/** Module-level cache/dedupe, keyed by Flow id — mirrors `entitySubtype.ts`'s `detailsCache`/`inFlight`. `null` means "fetched, no such Flow"; absent means "not yet fetched". */
const detailsCache = new Map<number, ResolvedFlowRef | null>()
const inFlight = new Map<number, Promise<ResolvedFlowRef | null>>()

async function fetchFlowRefDetails(flowId: number): Promise<ResolvedFlowRef | null> {
  try {
    const flow = await flowsApi.get(flowId)
    return { name: flow.name, description: flow.description }
  } catch {
    return null
  }
}

function loadFlowRefDetails(flowId: number): Promise<ResolvedFlowRef | null> {
  if (detailsCache.has(flowId)) return Promise.resolve(detailsCache.get(flowId) ?? null)
  let promise = inFlight.get(flowId)
  if (!promise) {
    promise = fetchFlowRefDetails(flowId).then((result) => {
      detailsCache.set(flowId, result)
      inFlight.delete(flowId)
      return result
    })
    inFlight.set(flowId, promise)
  }
  return promise
}

/**
 * The resolved target Flow's `name`/`description` for `flowId` — `undefined`
 * while unresolved (not yet fetched, or still loading), `null` once the
 * fetch has settled and found no such Flow, or the resolved value. Backs
 * `FlowNodeComponent`'s client-side fallback for a step with no
 * server-resolved `refStatus` entry yet (mirroring
 * `useEntityRefDetails`) — never used to write into the step itself.
 */
export function useFlowRefDetails(flowId: number | null | undefined): ResolvedFlowRef | null | undefined {
  const [details, setDetails] = useState<ResolvedFlowRef | null | undefined>(() => {
    if (flowId == null) return undefined
    return detailsCache.has(flowId) ? (detailsCache.get(flowId) ?? null) : undefined
  })

  useEffect(() => {
    if (flowId == null) {
      setDetails(undefined)
      return
    }
    if (detailsCache.has(flowId)) {
      setDetails(detailsCache.get(flowId) ?? null)
      return
    }
    setDetails(undefined)
    let cancelled = false
    loadFlowRefDetails(flowId).then((result) => {
      if (!cancelled) setDetails(result ?? null)
    })
    return () => {
      cancelled = true
    }
  }, [flowId])

  return details
}
