// @vitest-environment jsdom
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { HighlightedText } from './HighlightedText'

afterEach(cleanup)

function marked(text: string, matches: [number, number][]) {
  const { container } = render(<HighlightedText snippet={{ text, matches }} />)
  return {
    container,
    marks: Array.from(container.querySelectorAll('mark')).map((mark) => mark.textContent),
  }
}

describe('HighlightedText', () => {
  it('marks the range it is given, whatever the engine matched', () => {
    // A typo of the query: only the offsets say which word was matched.
    const { marks, container } = marked('a payment gateway', [[2, 9]])

    expect(marks).toEqual(['payment'])
    expect(container.textContent).toBe('a payment gateway')
  })

  it('marks the intended word after an emoji when offsets are in UTF-16 units', () => {
    // The API counts an emoji as two units, the way a JavaScript string does.
    const { marks, container } = marked('\u{1F600} payment gateway', [[3, 10]])

    expect(marks).toEqual(['payment'])
    expect(container.textContent).toBe('\u{1F600} payment gateway')
  })

  it('marks a word that contains an emoji', () => {
    const { marks } = marked('pay\u{1F600}ment end', [[0, 9]])

    expect(marks).toEqual(['pay\u{1F600}ment'])
  })

  it('marks several words', () => {
    expect(marked('pay the gateway', [[0, 3], [8, 15]]).marks).toEqual(['pay', 'gateway'])
  })

  it('keeps the whole text when offsets are unordered, overlapping or out of range', () => {
    const text = 'a payment gateway'
    for (const matches of [
      [[10, 17], [2, 9]],
      [[2, 9], [5, 12]],
      [[2, 99]],
      [[40, 50]],
      [[-3, 2]],
      [[4, 4]],
    ] as [number, number][][]) {
      const { container } = marked(text, matches)
      expect(container.textContent).toBe(text)
      cleanup()
    }
  })
})
