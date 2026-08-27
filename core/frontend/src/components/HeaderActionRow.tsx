import type { ReactNode } from 'react'

interface HeaderActionRowProps {
  left: ReactNode
  right?: ReactNode
}

/** Title-left/actions-right flex header row shared by detail and form pages alike. */
export function HeaderActionRow({ left, right }: HeaderActionRowProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', margin: '12px 0' }}>
      {left}
      {right}
    </div>
  )
}
