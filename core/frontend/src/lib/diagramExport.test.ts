// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { exportBackgroundColor } from './diagramExport'

function elementWithBackgroundToken(value: string | null): HTMLElement {
  const element = document.createElement('div')
  if (value !== null) element.style.setProperty('--g-color-base-background', value)
  document.body.append(element)
  return element
}

afterEach(() => document.body.replaceChildren())

describe('exportBackgroundColor', () => {
  it('uses the light theme background for a non-transparent export', () => {
    expect(exportBackgroundColor(elementWithBackgroundToken('#ffffff'), false)).toBe('#ffffff')
  })

  it('uses the dark theme background for a non-transparent export', () => {
    expect(exportBackgroundColor(elementWithBackgroundToken(' #221d22 '), false)).toBe('#221d22')
  })

  it('stays transparent when transparency is requested, in either theme', () => {
    expect(exportBackgroundColor(elementWithBackgroundToken('#221d22'), true)).toBeUndefined()
    expect(exportBackgroundColor(elementWithBackgroundToken('#ffffff'), true)).toBeUndefined()
  })

  it('falls back to white when the token is not defined', () => {
    expect(exportBackgroundColor(elementWithBackgroundToken(null), false)).toBe('#ffffff')
  })
})
