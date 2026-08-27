import { Label, Link, Text } from '@gravity-ui/uikit'
import { MarkdownDescription } from 'frontend/components/MarkdownDescription'
import { RelationTargetLink } from 'frontend/components/RelationTargetLink'
import { useSession } from 'frontend/lib/SessionContext'
import type { ApiEntity } from 'frontend/lib/types'
import { DirectionBadge } from './DirectionBadge'
import { OperationConsumersGraph } from './OperationConsumersGraph'
import { RoleBadge } from './RoleBadge'
import type { Operation, OperationConsumers } from '../lib/types'
import './OperationOverviewTab.css'

const CARD_STYLE = { border: '1px solid var(--g-color-line-generic)', borderRadius: 8, padding: 16 }

// Layout intentionally duplicated, not shared, with EndpointOverviewTab.tsx.
// Mirror layout-only
// changes made to that file here (and vice versa).
/** Overview tab: documentation, Channel/Details cards, the document-owner's implied role (no `ServiceOperationUsage` row needed for it), a compact message summary, and the channel-scoped publishers/subscribers graph — full service list lives on the Linked services tab, reached via "View all". */
export function OperationOverviewTab({
  operation,
  api,
  consumers,
  consumersLoading,
  consumersError,
  onRetryConsumers,
  onViewLinkedServices,
  linkedServicesTotal,
}: {
  operation: Operation
  api: ApiEntity | undefined
  /** Channel-scoped aggregation feeding the graph — deliberately not the same data as `linkedServicesTotal` below, since it can include participants from other API documents sharing this channel. */
  consumers: OperationConsumers | null
  consumersLoading: boolean
  consumersError: Error | null
  onRetryConsumers: () => void
  onViewLinkedServices: () => void
  linkedServicesTotal: number
}) {
  const { session } = useSession()
  const canLinkService = operation.status === 'active' && Boolean(session?.isAuthenticated)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="operation-overview-grid">
        <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <section>
            <Text variant="subheader-2" style={{ display: 'block', marginBottom: 12 }}>Documentation</Text>
            <div style={CARD_STYLE}>
              <MarkdownDescription text={operation.description} emptyMessage="No documentation" />
            </div>
          </section>

          {/* Channel/Details row: each keeps its own card, sized side by side
              rather than merged into one list. flex: 1 + minHeight: 0 lets
              this row stretch to fill the left column's remaining height, and
              it's always the last left-column element (Message moves above
              it) so the flex-grow target never has to
              switch between a conditional section. */}
          <div className="operation-channel-details-row" style={{ flex: 1, minHeight: 0 }}>
            <section style={{ display: 'flex', flexDirection: 'column' }}>
              <Text variant="subheader-2" style={{ display: 'block', marginBottom: 12 }}>Channel</Text>
              <div style={{ ...CARD_STYLE, flex: 1, display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: 12, justifyContent: 'space-between' }}>
                  <div>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Address</Text>
                    <Text style={{ fontFamily: 'var(--g-text-code-font-family, monospace)' }}>{operation.channelAddress}</Text>
                  </div>
                  {operation.channelProtocol && (
                    <div>
                      <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Protocol</Text>
                      <Label>{operation.channelProtocol}</Label>
                    </div>
                  )}
                  <div>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Direction</Text>
                    <DirectionBadge direction={operation.direction} />
                  </div>
                  {operation.provider && (
                    <div>
                      <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Document owner</Text>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <RelationTargetLink target={operation.provider.service.ref} targetKind="component" targetId={operation.provider.service.id} />
                        <RoleBadge role={operation.provider.role} />
                      </div>
                    </div>
                  )}
                  {operation.externalDocs?.url && (
                    <div>
                      <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>External docs</Text>
                      <Link href={operation.externalDocs.url} target="_blank">
                        {operation.externalDocs.description || operation.externalDocs.url}
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section style={{ display: 'flex', flexDirection: 'column' }}>
              <Text variant="subheader-2" style={{ display: 'block', marginBottom: 12 }}>Details</Text>
              <div style={{ ...CARD_STYLE, flex: 1, display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: 12, justifyContent: 'space-between' }}>
                  <div>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Operation ID</Text>
                    <div>{operation.operationId || '—'}</div>
                  </div>
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
                    </>
                  )}
                  {operation.tags.length > 0 && (
                    <div>
                      <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Tags</Text>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {operation.tags.map((tag) => <Label key={tag}>{tag}</Label>)}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </section>
          </div>

          {operation.messages.length > 0 && (
            <section>
              <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>
                Message{operation.messages.length > 1 ? 's' : ''}
              </Text>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {operation.messages.map((message, index) => (
                  <div
                    key={message.name || index}
                    style={{ padding: '6px 0', borderBottom: '1px solid var(--g-color-line-generic)' }}
                  >
                    <Text>{message.title || message.name || `Message ${index + 1}`}</Text>
                    {message.summary && <Text color="secondary" style={{ display: 'block' }}>{message.summary}</Text>}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <section style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <Text variant="subheader-2">Publishers & subscribers</Text>
            {linkedServicesTotal > 0 && (
              <Link
                href="#"
                onClick={(event) => { event.preventDefault(); onViewLinkedServices() }}
              >
                View all {linkedServicesTotal} service{linkedServicesTotal === 1 ? '' : 's'}
              </Link>
            )}
          </div>
          {/* flex: 1 + minHeight: 0 lets the graph grow past its default
              height to match the Channel/Details row's height — keeps their
              bottom edges level, same trick as EndpointOverviewTab's Details. */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <OperationConsumersGraph
              consumers={consumers}
              isLoading={consumersLoading}
              error={consumersError}
              onRetry={onRetryConsumers}
              canLinkService={canLinkService}
              onLinkService={onViewLinkedServices}
            />
          </div>
        </section>
      </div>
    </div>
  )
}
