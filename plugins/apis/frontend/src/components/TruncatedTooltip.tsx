// Shows a tooltip with the full text only when the wrapped text is actually
// cut off by `ellipsis`. Truncation is measured on hover, by the outer
// element's own handler (Tooltip injects its handlers into its child, so
// measuring there could be overridden).
import { useRef, useState, type ReactNode } from 'react'
import { Tooltip } from '@gravity-ui/uikit'

interface TruncatedTooltipProps {
  content: string
  placement?: 'top' | 'bottom'
  children: ReactNode
}

export function TruncatedTooltip({ content, placement = 'top', children }: TruncatedTooltipProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [truncated, setTruncated] = useState(false)

  const measure = () => {
    const el = ref.current?.firstElementChild as HTMLElement | null
    setTruncated(!!el && el.scrollWidth > el.clientWidth)
  }

  return (
    <div ref={ref} onMouseEnter={measure}>
      <Tooltip content={content} placement={placement} disabled={!truncated}>
        {children as React.ReactElement}
      </Tooltip>
    </div>
  )
}
