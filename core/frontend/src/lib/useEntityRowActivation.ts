import { useRef, useState } from 'react'

/**
 * Shared click-vs-fast-second-click logic for entity list tables: a click always opens/retargets the preview panel immediately,
 * and a second click on the same row within 400ms additionally navigates to its detail page.
 */
export function useEntityRowActivation<T>(getId: (item: T) => string, onOpenDetail: (item: T) => void) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const lastClickRef = useRef<{ id: string; time: number } | null>(null)

  function handleRowClick(item: T) {
    const id = getId(item)
    const now = Date.now()
    const isFastSecondClick = lastClickRef.current?.id === id && now - lastClickRef.current.time < 400
    lastClickRef.current = { id, time: now }
    setSelectedId(id)
    if (isFastSecondClick) onOpenDetail(item)
  }

  return { selectedId, setSelectedId, handleRowClick }
}
