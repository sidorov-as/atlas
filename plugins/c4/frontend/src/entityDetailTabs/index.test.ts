import { describe, expect, it } from 'vitest'
import { c4EntityDetailTabs } from './index'

function entity(kind: string, capabilities: string[]) {
  return { kind, capabilities } as { kind: string; capabilities: string[] }
}

describe('c4EntityDetailTabs', () => {
  it('shows the System tabs only for a System declaring architecture.subject.v1', () => {
    const system = entity('System', ['architecture.subject.v1'])
    const contextTab = c4EntityDetailTabs.find((tab) => tab.id === 'atlas.c4.system.context')!
    const architectureTab = c4EntityDetailTabs.find((tab) => tab.id === 'atlas.c4.system.architecture')!

    expect(contextTab.when(system)).toBe(true)
    expect(architectureTab.when(system)).toBe(true)
  })

  it('does not show the System tabs on a capability-declaring entity of a different kind', () => {
    const component = entity('Component', ['architecture.subject.v1'])
    const contextTab = c4EntityDetailTabs.find((tab) => tab.id === 'atlas.c4.system.context')!

    expect(contextTab.when(component)).toBe(false)
  })

  it('shows the Component diagram tab only for a Component declaring architecture.subject.v1', () => {
    const component = entity('Component', ['architecture.subject.v1'])
    const diagramTab = c4EntityDetailTabs.find((tab) => tab.id === 'atlas.c4.component.diagram')!

    expect(diagramTab.when(component)).toBe(true)
  })

  it('hides every tab when the entity does not declare the capability', () => {
    const system = entity('System', [])
    const component = entity('Component', [])

    for (const tab of c4EntityDetailTabs) {
      expect(tab.when(system)).toBe(false)
      expect(tab.when(component)).toBe(false)
    }
  })
})
