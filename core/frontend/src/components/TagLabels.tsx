import { Label } from '@gravity-ui/uikit'
import { tagColorKey } from '../lib/types'

export function TagLabels({ tags, tagColors }: { tags: string[]; tagColors: Record<string, string> }) {
  if (tags.length === 0) return '—'
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {tags.map((tag) => (
        <Label key={tag} theme="clear" className={`tag-label tag-preset-${tagColorKey(tagColors[tag])}`}>
          {tag}
        </Label>
      ))}
    </div>
  )
}
