// Pure helpers the full-screen graphs share when they are grouped: which
// groups to draw while a search narrows them, and how the Services of the
// expanded groups share the node cap.

import type { ConsumerGroup, ConsumerGroupBy, ServiceSummary } from './types'

/** The id of the team or system `service` belongs to, `null` when it has none for this grouping. */
export function groupIdOf(service: ServiceSummary, groupBy: ConsumerGroupBy): string | null {
  return groupBy === 'team' ? service.teamId : service.systemId
}

export interface ResolvedGroup extends ConsumerGroup {
  /** Services of the group matching the search; equals `count` when no search is active. */
  matches: number
  /** The group's size without the search; set only while a search is active (drives "N of M matches"). */
  total?: number
  /** A search is active and nothing in the group matches. */
  dimmed: boolean
}

/**
 * The groups to draw and the plain Services to draw beside them.
 *
 * Without a search these are the unsearched response's own. With a search the
 * group structure stays the unsearched one (so it does not jump), each group
 * carries its match count, and a group the server folded into a single plain
 * match (or dropped) is still drawn: one match counts from the plain list, no
 * match dims it. Plain matches that belong to a drawn group are not drawn
 * again — they are inside that group.
 */
export function resolveGroups<S>(
  base: { groups: ConsumerGroup[]; plain: S[] },
  searched: { groups: ConsumerGroup[]; plain: S[] } | null,
  groupIdOfPlain: (item: S) => string | null,
): { groups: ResolvedGroup[]; plain: S[] } {
  if (!searched) {
    return { groups: base.groups.map((group) => ({ ...group, matches: group.count, dimmed: false })), plain: base.plain }
  }
  const searchedCounts = new Map(searched.groups.map((group) => [group.id, group.count]))
  const plainMatches = new Map<string, number>()
  for (const item of searched.plain) {
    const id = groupIdOfPlain(item)
    if (id) plainMatches.set(id, (plainMatches.get(id) ?? 0) + 1)
  }
  const baseIds = new Set(base.groups.map((group) => group.id))
  const groups = base.groups.map((group): ResolvedGroup => {
    const matches = searchedCounts.get(group.id) ?? plainMatches.get(group.id) ?? 0
    return { ...group, count: matches, matches, total: group.count, dimmed: matches === 0 }
  })
  const plain = searched.plain.filter((item) => {
    const id = groupIdOfPlain(item)
    return id === null || !baseIds.has(id)
  })
  return { groups, plain }
}

/**
 * Shares `budget` Service nodes among expanded groups, in the order given.
 * Each group draws as many of its loaded members as the budget still allows;
 * `more` is what the group has beyond what is drawn (its total minus the drawn).
 */
export function allocateMembers<S>(
  expanded: { key: string; members: S[]; total: number }[],
  budget: number,
): Map<string, { drawn: S[]; more: number }> {
  const result = new Map<string, { drawn: S[]; more: number }>()
  let remaining = Math.max(0, budget)
  for (const group of expanded) {
    const drawn = group.members.slice(0, remaining)
    remaining -= drawn.length
    result.set(group.key, { drawn, more: Math.max(0, group.total - drawn.length) })
  }
  return result
}
