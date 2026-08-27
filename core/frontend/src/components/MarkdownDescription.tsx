import ReactMarkdown from 'react-markdown'
import type { ReactNode } from 'react'
import { Text } from '@gravity-ui/uikit'

const YFM_NOTE = /^\s*{%\s*note(?:\s+([\w-]+))?(?:\s+"([^"]+)")?\s*%}\s*\n([\s\S]*?)^\s*{%\s*endnote\s*%}\s*$/gm

/** Renders standard Markdown plus safe, non-interactive YFM note directives. */
function renderMarkdown(text: string): ReactNode[] {
  const normalizedText = text
    .replace(/^\s*{%\s*list tabs\s*%}\s*$/gm, '### Tabs')
    .replace(/^\s*{%\s*endlist\s*%}\s*$/gm, '')
  const nodes: ReactNode[] = []
  let cursor = 0
  let match: RegExpExecArray | null
  while ((match = YFM_NOTE.exec(normalizedText)) !== null) {
    if (match.index > cursor) nodes.push(<ReactMarkdown key={cursor}>{normalizedText.slice(cursor, match.index)}</ReactMarkdown>)
    const type = match[1] ?? 'note'
    const label = match[2] ?? `${type[0].toUpperCase()}${type.slice(1)}`
    nodes.push(
      <section key={match.index} className={`markdown-note markdown-note--${type}`}>
        <strong className="markdown-note__title">{label}</strong>
        <ReactMarkdown>{match[3].trim()}</ReactMarkdown>
      </section>,
    )
    cursor = match.index + match[0].length
  }
  if (cursor < normalizedText.length || nodes.length === 0) nodes.push(<ReactMarkdown key={cursor}>{normalizedText.slice(cursor)}</ReactMarkdown>)
  return nodes
}

/**
 * Read-only safe Markdown viewer for descriptions and full documentation.
 * and TeamDetailPage. Uses `react-markdown` rather than
 * `@gravity-ui/markdown-editor`'s viewer — that package's read-only path still pulls
 * its full editor dependency tree, adding ~330KB gzip for text-only rendering.
 */
export function MarkdownDescription({ text, emptyMessage = 'No description' }: { text: string; emptyMessage?: string }) {
  if (!text.trim()) {
    return <Text color="secondary">{emptyMessage}</Text>
  }
  return (
    <div className="markdown-description">
      {renderMarkdown(text)}
    </div>
  )
}
