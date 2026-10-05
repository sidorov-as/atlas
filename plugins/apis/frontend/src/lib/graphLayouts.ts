// Pure placement functions for the dependency graphs. Each returns top-left
// positions (React Flow's coordinate convention) for nodes around a center
// node whose box is centered on the origin. The graphs are stars, so a
// hand-written placement is enough — no layout library. The compact inline
// graphs use `ringsLayout`; the full-screen graphs use the Columns layouts.

export interface NodeSize {
  width: number
  height: number
}

export interface Position {
  x: number
  y: number
}

/** Radius of the innermost ring — the compact graph's long-standing radius. */
export const RING_RADIUS = 220
const RING_GAP = 8
// Starts at the top, so the first node sits directly above the center.
const FULL_CIRCLE: [number, number] = [-Math.PI / 2, (3 * Math.PI) / 2]

const LEVEL_GAP_X = 56
const ROW_GAP_Y = 16
const CENTER_GAP_X = 80

function overlaps(a: Position, b: Position, size: NodeSize, gap: number): boolean {
  return Math.abs(a.x - b.x) < size.width + gap && Math.abs(a.y - b.y) < size.height + gap
}

function anglesOnRing(count: number, [start, end]: [number, number], isFullCircle: boolean): number[] {
  if (count === 1) return [(start + end) / 2]
  const step = isFullCircle ? (end - start) / count : (end - start) / (count - 1)
  return Array.from({ length: count }, (_, index) => start + step * index)
}

function centersOnRing(count: number, radius: number, arc: [number, number], isFullCircle: boolean): Position[] {
  return anglesOnRing(count, arc, isFullCircle).map((angle) => ({ x: radius * Math.cos(angle), y: radius * Math.sin(angle) }))
}

/** True when `count` evenly spread nodes on this ring leave no two neighbours overlapping. */
function fitsOnRing(count: number, radius: number, arc: [number, number], isFullCircle: boolean, size: NodeSize): boolean {
  if (count <= 1) return true
  const centers = centersOnRing(count, radius, arc, isFullCircle)
  const pairs = isFullCircle ? count : count - 1
  for (let index = 0; index < pairs; index += 1) {
    if (overlaps(centers[index], centers[(index + 1) % count], size, RING_GAP)) return false
  }
  return true
}

/**
 * Concentric rings: ring `k` has radius `RING_RADIUS + k * (node diagonal + RING_GAP)`
 * and holds as many nodes as fit without overlapping their neighbours; the
 * rest spill onto the next ring. `arc` restricts the nodes to an angular span
 * (radians) — used by Operations to keep publishers and subscribers on
 * opposite sides.
 */
export function ringsLayout(count: number, size: NodeSize, arc: [number, number] = FULL_CIRCLE): Position[] {
  const isFullCircle = arc[1] - arc[0] >= 2 * Math.PI
  // Center-to-center distance between rings: the box diagonal, so boxes on adjacent rings can never overlap at any angular offset.
  const ringStep = Math.hypot(size.width, size.height) + RING_GAP
  const positions: Position[] = []
  let ring = 0
  while (positions.length < count) {
    const radius = RING_RADIUS + ring * ringStep
    const remaining = count - positions.length
    let onRing = 1
    while (onRing < remaining && fitsOnRing(onRing + 1, radius, arc, isFullCircle, size)) onRing += 1
    for (const center of centersOnRing(onRing, radius, arc, isFullCircle)) {
      positions.push({ x: center.x - size.width / 2, y: center.y - size.height / 2 })
    }
    ring += 1
  }
  return positions
}

// --- Full-screen layout --------------------------------------------------------
// An *item* is what the layout places: a plain node, a collapsed group, or an
// expanded group — its card plus `members` Services (and a possible "+N more"
// node) that all share one member size. Items keep the order they are given in.

export interface LayoutItem {
  /** The box of the item's own node (a Service, a "more" node or a group card). */
  size: NodeSize
  /** Number of member nodes of an expanded group; 0 or absent for every other item. */
  members?: number
}

export interface ItemPlacement {
  /** Top-left of the item's own node. */
  position: Position
  /** Top-left of each member node, in member order. */
  members: Position[]
}

/**
 * The full-screen layout: strict levels from the center outward, one column
 * per level, like a left-to-right tree. Level 1 stacks the items top to bottom
 * beside the center node, centered vertically. An expanded group's members are
 * level 2: one column on the outer side of its card, vertically centered on the
 * card, with the items below it moved down by the block's extra height so no
 * two blocks overlap. Every edge then joins neighbouring levels. `side` picks
 * which side of the center everything grows towards.
 */
export function columnsItemsLayout(
  items: LayoutItem[],
  memberSize: NodeSize,
  center: NodeSize,
  side: 'left' | 'right' = 'right',
): ItemPlacement[] {
  const direction = side === 'right' ? 1 : -1
  // Maps the outward distance of a box's inner edge to its top-left x.
  const toX = (inner: number, width: number) => (direction > 0 ? inner : -inner - width)
  const inner = center.width / 2 + CENTER_GAP_X
  const cardWidth = Math.max(0, ...items.map((item) => item.size.width))
  const memberInner = inner + cardWidth + LEVEL_GAP_X

  const blockHeights = items.map((item) => {
    const members = item.members ?? 0
    return members > 0 ? members * memberSize.height + (members - 1) * ROW_GAP_Y : 0
  })
  const slots = items.map((item, index) => Math.max(item.size.height, blockHeights[index]))
  const totalHeight = slots.reduce((sum, height) => sum + height, 0) + Math.max(0, items.length - 1) * ROW_GAP_Y

  let top = -totalHeight / 2
  return items.map((item, index) => {
    const blockTop = top + (slots[index] - blockHeights[index]) / 2
    const placement: ItemPlacement = {
      position: { x: toX(inner, item.size.width), y: top + (slots[index] - item.size.height) / 2 },
      members: Array.from({ length: item.members ?? 0 }, (_, member) => ({
        x: toX(memberInner, memberSize.width),
        y: blockTop + member * (memberSize.height + ROW_GAP_Y),
      })),
    }
    top += slots[index] + ROW_GAP_Y
    return placement
  })
}

/** Plain nodes in the full-screen level-1 column — `columnsItemsLayout` without any group. */
export function columnsLayout(count: number, size: NodeSize, center: NodeSize, side: 'left' | 'right' = 'right'): Position[] {
  return columnsItemsLayout(Array.from({ length: count }, () => ({ size })), size, center, side).map((placement) => placement.position)
}

/** Case-insensitive match of a Service's name or display name — mirrors what the server's `search` matches. */
export function serviceMatchesQuery(service: { name: string; title?: string | null }, query: string): boolean {
  const needle = query.trim().toLowerCase()
  return needle !== '' && (service.name.toLowerCase().includes(needle) || (service.title ?? '').toLowerCase().includes(needle))
}
