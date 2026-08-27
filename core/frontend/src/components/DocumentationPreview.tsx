import { lazy, Suspense } from 'react'
import { Loader, Text } from '@gravity-ui/uikit'

const DocumentationPreviewView = lazy(() => import('./DocumentationPreviewView'))

/**
 * Lazily renders full documentation with Diplodoc's YFM transformer so the
 * authoring editor and transformer stay out of list and header routes.
 */
export function DocumentationPreview({ value, emptyMessage = 'No documentation' }: { value: string; emptyMessage?: string }) {
  if (!value.trim()) return <Text color="secondary">{emptyMessage}</Text>

  return (
    <Suspense fallback={<Loader size="s" />}>
      <DocumentationPreviewView value={value} />
    </Suspense>
  )
}
