import { Fragment } from 'react'
import type { SearchSnippet } from '../lib/api'

/**
 * Renders snippet text with its match ranges wrapped in `<mark>`. Everything goes through
 * React text nodes, so markup in indexed content is displayed literally, never parsed.
 */
export function HighlightedText({ snippet }: { snippet: SearchSnippet }) {
  const { text } = snippet
  const ranges = [...snippet.matches]
    .filter(([start, end]) => start >= 0 && end > start && start < text.length)
    .sort((a, b) => a[0] - b[0])

  const parts: React.ReactNode[] = []
  let cursor = 0
  ranges.forEach(([start, end], index) => {
    if (start < cursor) return
    const clampedEnd = Math.min(end, text.length)
    if (start > cursor) parts.push(<Fragment key={`t${index}`}>{text.slice(cursor, start)}</Fragment>)
    parts.push(<mark key={`m${index}`}>{text.slice(start, clampedEnd)}</mark>)
    cursor = clampedEnd
  })
  if (cursor < text.length) parts.push(<Fragment key="tail">{text.slice(cursor)}</Fragment>)
  return <>{parts}</>
}
