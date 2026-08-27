import { lazy, Suspense } from 'react'
import { Loader } from '@gravity-ui/uikit'

const DocumentationEditorView = lazy(() => import('./DocumentationEditorView'))

/** Lazily loads the rich Markdown editor so detail and list routes stay lightweight. */
export function DocumentationEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <Suspense fallback={<Loader size="s" />}>
      <DocumentationEditorView value={value} onChange={onChange} />
    </Suspense>
  )
}
