import { describe, expect, it } from 'vitest'
import { columnsItemsLayout, columnsLayout, ringsLayout, RING_RADIUS, serviceMatchesQuery, type ItemPlacement, type LayoutItem, type NodeSize, type Position } from './graphLayouts'

const SERVICE: NodeSize = { width: 180, height: 52 }
const SERVICE_ROLE: NodeSize = { width: 180, height: 80 }
const CENTER: NodeSize = { width: 200, height: 84 }
const PUBLISHER_ARC: [number, number] = [Math.PI * 0.7, Math.PI * 1.3]
const SUBSCRIBER_ARC: [number, number] = [Math.PI * -0.3, Math.PI * 0.3]

function boxesOverlap(a: Position, sizeA: NodeSize, b: Position, sizeB: NodeSize): boolean {
  return a.x < b.x + sizeB.width && b.x < a.x + sizeA.width && a.y < b.y + sizeB.height && b.y < a.y + sizeA.height
}

function expectNoOverlap(boxes: { position: Position; size: NodeSize }[]) {
  for (let i = 0; i < boxes.length; i += 1) {
    for (let j = i + 1; j < boxes.length; j += 1) {
      expect(
        boxesOverlap(boxes[i].position, boxes[i].size, boxes[j].position, boxes[j].size),
        `nodes ${i} and ${j} overlap`,
      ).toBe(false)
    }
  }
}

const centerBox = { position: { x: -CENTER.width / 2, y: -CENTER.height / 2 }, size: CENTER }

describe('ringsLayout', () => {
  it.each([6, 7, 18, 50])('places %i nodes without overlap, including the center node', (count) => {
    const positions = ringsLayout(count, SERVICE)
    expect(positions).toHaveLength(count)
    expectNoOverlap([centerBox, ...positions.map((position) => ({ position, size: SERVICE }))])
  })

  it('keeps 7 nodes on the first ring at the default radius', () => {
    const positions = ringsLayout(7, SERVICE)
    for (const position of positions) {
      const radius = Math.hypot(position.x + SERVICE.width / 2, position.y + SERVICE.height / 2)
      expect(radius).toBeCloseTo(RING_RADIUS)
    }
  })

  it('spills onto more than one ring at 18 nodes', () => {
    const radii = new Set(
      ringsLayout(18, SERVICE).map((p) => Math.round(Math.hypot(p.x + SERVICE.width / 2, p.y + SERVICE.height / 2))),
    )
    expect(radii.size).toBeGreaterThan(1)
  })

  it('returns nothing for zero nodes and a single node on the first ring', () => {
    expect(ringsLayout(0, SERVICE)).toEqual([])
    expect(ringsLayout(1, SERVICE)).toHaveLength(1)
  })

  it('keeps publishers and subscribers apart on opposite arcs without overlap', () => {
    for (const [publishers, subscribers] of [[3, 3], [20, 20], [30, 1]]) {
      const left = ringsLayout(publishers, SERVICE_ROLE, PUBLISHER_ARC)
      const right = ringsLayout(subscribers, SERVICE_ROLE, SUBSCRIBER_ARC)
      expect(left.every((position) => position.x < 0)).toBe(true)
      expect(right.every((position) => position.x > 0)).toBe(true)
      expectNoOverlap([centerBox, ...[...left, ...right].map((position) => ({ position, size: SERVICE_ROLE }))])
    }
  })
})

describe('columnsLayout', () => {
  it('stacks every node in one column beside the center, centered vertically', () => {
    const positions = columnsLayout(25, SERVICE, CENTER)
    expect(positions).toHaveLength(25)
    expect(positions.every((position) => position.x > CENTER.width / 2)).toBe(true)
    // One level, one column: no matter how many nodes, they all share one x.
    expect(new Set(positions.map((position) => position.x)).size).toBe(1)
    const centers = positions.map((position) => position.y + SERVICE.height / 2)
    expect(centers[0] + centers[24]).toBeCloseTo(0)
    expectNoOverlap([centerBox, ...positions.map((position) => ({ position, size: SERVICE }))])
  })

  it('mirrors to the left of the center for the other side', () => {
    const positions = columnsLayout(12, SERVICE_ROLE, CENTER, 'left')
    expect(positions.every((position) => position.x + SERVICE_ROLE.width < -CENTER.width / 2)).toBe(true)
    expectNoOverlap([centerBox, ...positions.map((position) => ({ position, size: SERVICE_ROLE }))])
  })

  it('keeps two-sided publishers and subscribers on opposite sides', () => {
    const left = columnsLayout(11, SERVICE_ROLE, CENTER, 'left')
    const right = columnsLayout(11, SERVICE_ROLE, CENTER, 'right')
    expectNoOverlap([centerBox, ...[...left, ...right].map((position) => ({ position, size: SERVICE_ROLE }))])
  })
})

const GROUP_CARD: NodeSize = { width: 180, height: 64 }
const MEMBER: NodeSize = SERVICE

function itemBoxes(items: LayoutItem[], placements: ItemPlacement[]) {
  return placements.flatMap((placement, index) => [
    { position: placement.position, size: items[index].size },
    ...placement.members.map((position) => ({ position, size: MEMBER })),
  ])
}

function makeItems(plain: number, groups: number[]): LayoutItem[] {
  // `groups` holds the member count of each expanded group; collapsed groups are plain cards too.
  return [
    ...groups.map((members) => ({ size: GROUP_CARD, members })),
    ...Array.from({ length: plain }, () => ({ size: GROUP_CARD })),
  ]
}

describe('columnsItemsLayout', () => {
  it.each([
    ['no expanded group', []],
    ['one expanded group', [12]],
    ['three expanded groups', [3, 25, 7]],
  ])('never overlaps with %s', (_label, groups) => {
    const items = makeItems(8, groups)
    const placements = columnsItemsLayout(items, MEMBER, CENTER, 'right')
    expectNoOverlap([centerBox, ...itemBoxes(items, placements)])
  })

  it('places the member block beside the card and shifts the items below it down', () => {
    const collapsed = columnsItemsLayout(makeItems(3, []), MEMBER, CENTER, 'right')
    const expanded = columnsItemsLayout(makeItems(2, [12]), MEMBER, CENTER, 'right')
    const [group] = expanded
    expect(group.members).toHaveLength(12)
    expect(group.members.every((member) => member.x >= group.position.x + GROUP_CARD.width)).toBe(true)
    // The item after the expanded group sits lower than it would with every group collapsed.
    expect(expanded[1].position.y).toBeGreaterThan(collapsed[1].position.y)
  })

  it('keeps strict levels: every card in one column and every member in one column', () => {
    const items = makeItems(12, [30, 12])
    const placements = columnsItemsLayout(items, MEMBER, CENTER, 'right')
    expect(new Set(placements.map((placement) => placement.position.x)).size).toBe(1)
    const memberXs = new Set(placements.flatMap((placement) => placement.members.map((member) => member.x)))
    expect(memberXs.size).toBe(1)
    expect([...memberXs][0]).toBeGreaterThanOrEqual(placements[0].position.x + GROUP_CARD.width)
    expectNoOverlap([centerBox, ...itemBoxes(items, placements)])
  })

  it('centers a member block on its card and moves the items below it past the block', () => {
    const items = makeItems(2, [20])
    const [group, next] = columnsItemsLayout(items, MEMBER, CENTER, 'right')
    const memberCenters = group.members.map((member) => member.y + MEMBER.height / 2)
    expect((memberCenters[0] + memberCenters[19]) / 2).toBeCloseTo(group.position.y + GROUP_CARD.height / 2)
    expect(next.position.y).toBeGreaterThanOrEqual(Math.max(...group.members.map((member) => member.y + MEMBER.height)))
  })

  it('mirrors to the left with blocks opening outward, away from the center', () => {
    const items = makeItems(4, [9])
    const left = columnsItemsLayout(items, MEMBER, CENTER, 'left')
    const right = columnsItemsLayout(items, MEMBER, CENTER, 'right')
    expect(left[0].position.x + GROUP_CARD.width).toBeLessThan(-CENTER.width / 2)
    expect(left[0].members.every((member) => member.x + MEMBER.width <= left[0].position.x)).toBe(true)
    expect(right[0].members.every((member) => member.x >= right[0].position.x + GROUP_CARD.width)).toBe(true)
    expectNoOverlap([centerBox, ...itemBoxes(items, left)])
  })

  it('keeps publisher and subscriber sides apart', () => {
    const publishers = makeItems(3, [6])
    const subscribers = makeItems(5, [14, 2])
    const left = columnsItemsLayout(publishers, MEMBER, CENTER, 'left')
    const right = columnsItemsLayout(subscribers, MEMBER, CENTER, 'right')
    expectNoOverlap([centerBox, ...itemBoxes(publishers, left), ...itemBoxes(subscribers, right)])
  })
})

describe('serviceMatchesQuery', () => {
  it('matches the name or the display name, case-insensitively', () => {
    const service = { name: 'billing-api', title: 'Billing Service' }
    expect(serviceMatchesQuery(service, 'BILLING-A')).toBe(true)
    expect(serviceMatchesQuery(service, 'ing serv')).toBe(true)
    expect(serviceMatchesQuery(service, 'payments')).toBe(false)
    expect(serviceMatchesQuery(service, '  ')).toBe(false)
  })
})
