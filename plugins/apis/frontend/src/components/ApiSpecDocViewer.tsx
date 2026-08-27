// Orchestrator loaded lazily by ApiSpecPanel's ApiDocumentationView. Delegates
// to a type-specific viewer (OpenApiViewer / AsyncApiViewer), each its own
// lazy chunk — a bug or bundle issue in one renderer must never affect the
// other type, or any page that isn't showing a Documentation tab at all.
// Split out of `frontend/components/ApiSpecDocViewer`.
import { lazy, Suspense, useMemo } from 'react'
import { Loader, Text } from '@gravity-ui/uikit'
import { ErrorBoundary } from 'react-error-boundary'
import { load as parseYaml } from 'js-yaml'
import type { ApiEntity, ApiType } from 'frontend/lib/types'

const OpenApiViewer = lazy(() => import('./OpenApiViewer'))
const AsyncApiViewer = lazy(() => import('./AsyncApiViewer'))

function parseSpecObject(content: string): Record<string, unknown> | null {
  try {
    const parsed = parseYaml(content)
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : null
  } catch {
    return null
  }
}

function looksLikeSpecType(parsed: Record<string, unknown>, type: ApiType): boolean {
  if (type === 'openapi') return 'openapi' in parsed || 'swagger' in parsed
  if (type === 'asyncapi') return 'asyncapi' in parsed
  return false
}

function UnrenderableSpecFallback({ api }: { api: ApiEntity }) {
  return (
    <Text color="secondary">This {api.spec.type.toUpperCase()} specification couldn't be rendered in the embedded viewer. Download it to inspect the source.</Text>
  )
}

export default function ApiSpecDocViewer({ api }: { api: ApiEntity }) {
  const { type, specContent } = api.spec
  const parsed = useMemo(() => parseSpecObject(specContent), [specContent])

  if (!parsed || !looksLikeSpecType(parsed, type)) {
    return <UnrenderableSpecFallback api={api} />
  }

  return (
    <ErrorBoundary fallback={<UnrenderableSpecFallback api={api} />} resetKeys={[specContent]}>
      <Suspense fallback={<Loader size="m" />}>
        {type === 'openapi' ? <OpenApiViewer spec={parsed} /> : <AsyncApiViewer schema={parsed} />}
      </Suspense>
    </ErrorBoundary>
  )
}
