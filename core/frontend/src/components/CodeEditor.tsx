import { lazy, Suspense } from 'react'
import { Loader } from '@gravity-ui/uikit'
import type { CodeEditorLanguage } from './CodeEditorView'

const CodeEditorViewLazy = lazy(() => import('./CodeEditorView'))

/** Lazily loads the Monaco-based code editor so routes/pages that don't render it don't pay its bundle cost. */
export function CodeEditor({
  value,
  onChange,
  language,
  error,
}: {
  value: string
  onChange: (value: string) => void
  language: CodeEditorLanguage
  error?: string | null
}) {
  return (
    <Suspense fallback={<Loader size="s" />}>
      <CodeEditorViewLazy value={value} onChange={onChange} language={language} error={error} />
    </Suspense>
  )
}

export type { CodeEditorLanguage }
