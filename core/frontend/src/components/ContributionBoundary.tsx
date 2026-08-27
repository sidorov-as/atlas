import type { ReactNode } from 'react'
import { Alert } from '@gravity-ui/uikit'
import { ErrorBoundary } from 'react-error-boundary'

function ContributionFailedFallback({ label }: { label: string }) {
  return <Alert theme="danger" title={`${label} failed to load`} message="This section couldn't be rendered." />
}

/** Isolates one contribution's render errors so it can't crash the shell or any sibling contribution (ADR 0020). */
export function ContributionBoundary({ label, children }: { label: string; children: ReactNode }) {
  return <ErrorBoundary fallback={<ContributionFailedFallback label={label} />}>{children}</ErrorBoundary>
}
