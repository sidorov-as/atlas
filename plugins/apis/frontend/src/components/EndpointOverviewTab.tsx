import { Label, Link, Text } from '@gravity-ui/uikit'
import { EntityTable } from 'frontend/components/EntityTable'
import { MarkdownDescription } from 'frontend/components/MarkdownDescription'
import { RelationTargetLink } from 'frontend/components/RelationTargetLink'
import { useSession } from 'frontend/lib/SessionContext'
import type { ApiEntity, Relation } from 'frontend/lib/types'
import { EndpointConsumersGraph } from './EndpointConsumersGraph'
import { EndpointParameterTable } from './EndpointParameterTable'
import { statusCodeTheme } from '../lib/badges'
import type { Endpoint, EndpointConsumers, EndpointResponse, EndpointSecurity } from '../lib/types'
import './EndpointOverviewTab.css'

const CARD_STYLE = { border: '1px solid var(--g-color-line-generic)', borderRadius: 8, padding: 16 }

/** A resolved security-scheme entry into a human-meaningful label, e.g. `http`+`bearer` -> `http (bearer)`. */
function formatSecurityLabel(entry: EndpointSecurity): string {
  return entry.scheme ? `${entry.type} (${entry.scheme})` : entry.type
}

/** Deduplicated content types across the request body and every response — the "Consumes/Produces are frontend-only" rendering. */
function computeContentTypes(endpoint: Endpoint): string[] {
  const contentTypes = [
    endpoint.request.body?.contentType,
    ...endpoint.responses.map((response) => response.contentType),
  ].filter((contentType): contentType is string => Boolean(contentType))
  return [...new Set(contentTypes)]
}

// Layout intentionally duplicated, not shared, with OperationOverviewTab.tsx.
// Mirror layout-only
// changes made to that file here (and vice versa).
/** Overview tab: documentation, Details (owner/system inherited from the parent API), parameter tables (omitted when empty), compact responses table, and the compact consumers graph — full service list lives on the Linked services tab, reached via "View all". */
export function EndpointOverviewTab({
  endpoint,
  api,
  consumers,
  consumersLoading,
  consumersError,
  onRetryConsumers,
  onViewLinkedServices,
  providerRelation,
}: {
  endpoint: Endpoint
  api: ApiEntity | undefined
  consumers: EndpointConsumers | null
  consumersLoading: boolean
  consumersError: Error | null
  onRetryConsumers: () => void
  onViewLinkedServices: () => void
  /** The API's `apiProvidedBy` relation, shown on the consumers graph's endpoint node — `null` if none is declared. */
  providerRelation: Relation | null
}) {
  const { session } = useSession()
  const canLinkService = endpoint.status === 'active' && Boolean(session?.isAuthenticated)
  const totalLinked = consumers?.count ?? 0

  const pathParams = endpoint.request.parameters.filter((parameter) => parameter.location === 'path')
  const queryParams = endpoint.request.parameters.filter((parameter) => parameter.location === 'query')
  const headerParams = endpoint.request.parameters.filter((parameter) => parameter.location === 'header')
  const contentTypes = computeContentTypes(endpoint)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="endpoint-overview-grid">
        <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <section>
            <Text variant="subheader-2" style={{ display: 'block', marginBottom: 12 }}>Documentation</Text>
            <div style={CARD_STYLE}>
              <MarkdownDescription text={endpoint.description} emptyMessage="No documentation" />
            </div>
          </section>

          <section style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <Text variant="subheader-2" style={{ display: 'block', marginBottom: 12 }}>Details</Text>
            <div className="endpoint-details-grid" style={{ ...CARD_STYLE, flex: 1 }}>
              <div>
                <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Operation ID</Text>
                <div>{endpoint.operationId || '—'}</div>
              </div>
              {api?.spec.resolvedProtocol && (
                <div>
                  <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Protocol</Text>
                  <div>{api.spec.resolvedProtocol}</div>
                </div>
              )}
              {api?.spec.resolvedBaseUrl && (
                <div>
                  <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Base URL</Text>
                  <div><code>{api.spec.resolvedBaseUrl}</code></div>
                </div>
              )}
              {contentTypes.length > 0 && (
                <div>
                  <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Consumes/Produces</Text>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {contentTypes.map((contentType) => <Label key={contentType}>{contentType}</Label>)}
                  </div>
                </div>
              )}
              {endpoint.security.length > 0 && (
                <div>
                  <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Security</Text>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {endpoint.security.map((entry) => <Label key={formatSecurityLabel(entry)}>{formatSecurityLabel(entry)}</Label>)}
                  </div>
                </div>
              )}
              {endpoint.externalDocs && (
                <div>
                  <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>External docs</Text>
                  <Link href={endpoint.externalDocs.url} target="_blank" rel="noreferrer">
                    {endpoint.externalDocs.description || endpoint.externalDocs.url}
                  </Link>
                </div>
              )}
              {api && (
                <>
                  <div>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Owner</Text>
                    <Label>
                      <RelationTargetLink target={api.spec.owner} targetKind="group" targetId={api.spec.ownerId} />
                    </Label>
                  </div>
                  <div>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>System</Text>
                    <Label>
                      <RelationTargetLink target={api.spec.system} targetKind="system" targetId={api.spec.systemId!} />
                    </Label>
                  </div>
                  <div>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Source</Text>
                    {/* An active endpoint on a synced (`openapi`, non-empty resolved spec) API is always spec-derived — everything else is manually authored via Django admin. */}
                    <div>{api.spec.type === 'openapi' && api.spec.specContent !== '' ? 'Imported from spec' : 'Manually authored'}</div>
                  </div>
                </>
              )}
              {endpoint.tags.length > 0 && (
                <div>
                  <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Tags</Text>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {endpoint.tags.map((tag) => <Label key={tag}>{tag}</Label>)}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>

        <section style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <Text variant="subheader-2">Services using this endpoint</Text>
            {totalLinked > 0 && (
              <Link
                href="#"
                onClick={(event) => { event.preventDefault(); onViewLinkedServices() }}
              >
                View all {totalLinked} service{totalLinked === 1 ? '' : 's'}
              </Link>
            )}
          </div>
          {/* flex: 1 + minHeight: 0 lets the graph grow past GRAPH_HEIGHT to match
              the row's height when a long Documentation card pushes Details taller
              than the graph's default size — keeps their bottom edges level. */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <EndpointConsumersGraph
              consumers={consumers}
              isLoading={consumersLoading}
              error={consumersError}
              onRetry={onRetryConsumers}
              canLinkService={canLinkService}
              onLinkService={onViewLinkedServices}
              providerRelation={providerRelation}
            />
          </div>
        </section>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <EndpointParameterTable title="Path parameters" parameters={pathParams} />
        <EndpointParameterTable title="Query parameters" parameters={queryParams} />
        <EndpointParameterTable title="Header parameters" parameters={headerParams} />

        {endpoint.responses.length > 0 && (
          <section>
            <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>Responses</Text>
            <EntityTable
              data={endpoint.responses}
              columns={[
                { id: 'statusCode', name: 'Status', template: (item: EndpointResponse) => <Label theme={statusCodeTheme(item.statusCode)}>{item.statusCode}</Label> },
                { id: 'description', name: 'Description', template: (item: EndpointResponse) => item.description || '—' },
                { id: 'contentType', name: 'Content type', template: (item: EndpointResponse) => item.contentType || '—' },
              ]}
              getRowId={(item: EndpointResponse) => item.statusCode}
            />
          </section>
        )}
      </div>
    </div>
  )
}
