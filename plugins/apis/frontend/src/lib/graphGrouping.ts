// Grouping choice of the full-screen dependency graphs: the stored value, the
// default rule and the stable color of a group. Kept next to `graphLayouts.ts`;
// the layout choice and this one are stored separately.

import { TAG_PALETTE, type TagColorKey } from 'frontend/lib/types'
import type { ConsumerGroupBy } from './types'

/** `none` is an explicit "never group", distinct from "nothing stored". */
export type GraphGroupingId = ConsumerGroupBy | 'none'

const GRAPH_GROUP_BY_STORAGE_KEY = 'atlas.apis.graphGroupBy'

/** Grouping starts on (by Team) once a graph holds at least this many linked Services. */
export const DEFAULT_GROUPING_THRESHOLD = 10

export function defaultGraphGrouping(totalCount: number): GraphGroupingId {
  return totalCount >= DEFAULT_GROUPING_THRESHOLD ? 'team' : 'none'
}

/** The grouping the user last chose in this browser, or `null` when nothing valid is stored (storage blocked, missing or unknown value) — the caller then applies the default rule. */
export function readGraphGrouping(): GraphGroupingId | null {
  try {
    const stored = window.localStorage.getItem(GRAPH_GROUP_BY_STORAGE_KEY)
    return stored === 'none' || stored === 'team' || stored === 'system' ? stored : null
  } catch {
    return null
  }
}

export function writeGraphGrouping(grouping: GraphGroupingId): void {
  try {
    window.localStorage.setItem(GRAPH_GROUP_BY_STORAGE_KEY, grouping)
  } catch {
    // Storage unavailable (private window, blocked site data): the choice just isn't remembered.
  }
}

/** The grouping to open a graph with: the stored choice, else the default rule for `totalCount` Services. */
export function resolveGraphGrouping(totalCount: number): GraphGroupingId {
  return readGraphGrouping() ?? defaultGraphGrouping(totalCount)
}

/** A stable tag-palette color for a group id, so a team keeps its color between graphs and sessions. */
export function groupColorKey(groupId: string): TagColorKey {
  let hash = 0
  for (let index = 0; index < groupId.length; index += 1) hash = (hash * 31 + groupId.charCodeAt(index)) >>> 0
  return TAG_PALETTE[hash % TAG_PALETTE.length]
}
