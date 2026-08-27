import { describe, expect, it } from 'vitest'
import { FLOW_NODE_PALETTE, FLOW_NODE_SWATCHES } from './flowNodePalette'

describe('FLOW_NODE_PALETTE', () => {
  it('gives System its own fixed color, distinct from API\'s', () => {
    expect(FLOW_NODE_PALETTE.system).toBe(FLOW_NODE_SWATCHES.success)
    expect(FLOW_NODE_PALETTE.system).not.toBe(FLOW_NODE_PALETTE.api)
  })

  it('gives Component the picker-only color that matches no real Component (subtype-derived) canvas color', () => {
    expect(FLOW_NODE_PALETTE.component).toBe(FLOW_NODE_SWATCHES.info)
    expect(FLOW_NODE_PALETTE.component).not.toBe(FLOW_NODE_SWATCHES.success)
  })
})
