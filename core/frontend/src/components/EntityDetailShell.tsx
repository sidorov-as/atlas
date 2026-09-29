import { useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Breadcrumbs, Button, Label, Link, Loader, Tab, TabList, TabPanel, TabProvider, Text } from '@gravity-ui/uikit'
import { ConfirmDialog } from './ConfirmDialog'
import { ConflictBanner } from './ConflictBanner'
import { ContributionBoundary } from './ContributionBoundary'
import { HeaderActionRow } from './HeaderActionRow'
import { MarkdownDescription } from './MarkdownDescription'
import { ReadOnlyBanner } from './ReadOnlyBanner'
import { TagLabels } from './TagLabels'
import { UnavailableEntityBanner } from './UnavailableEntityBanner'
import type { EntityDetailTabContribution } from '@atlas/plugin-api'
import { type CatalogEntityUnion, type ConflictReason, type LinkOut, type Metadata } from '../lib/types'
import { useConfirm } from '../lib/useConfirm'
import { useSession } from '../lib/SessionContext'

export interface RailField {
  label: string
  value: ReactNode
}

/** Right-rail links section. */
export function LinksRail({ links }: { links: LinkOut[] }) {
  if (links.length === 0) return null
  return (
    <>
      <Text variant="subheader-2" style={{ display: 'block', marginTop: 24 }}>
        Links
      </Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
        {links.map((link) => (
          <div key={link.url} style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
            <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <Link href={link.url} target="_blank" rel="noreferrer">
                {link.title || link.url}
              </Link>
            </div>
            {link.type && <div style={{ flexShrink: 0 }}><Label size="xs">{link.type}</Label></div>}
          </div>
        ))}
      </div>
    </>
  )
}

interface EntityDetailShellProps {
  breadcrumb: { label: string; to: string }
  metadata: Metadata | undefined
  ingestedFrom: string | null | undefined
  blockedBy?: string | null
  blockedByReason?: ConflictReason | null
  isLoading: boolean
  error: Error | null
  editTo: string
  /** Removed/Revive/Purge lifecycle actions — omitted entirely
   * for entity kinds with no such lifecycle (e.g. Group). Remove/Revive follow the same
   * ownership-based permission as Edit (`isManual`); Purge is shown whenever the entity is
   * `removed`, regardless of `isManual` — a Purge Grant is a deliberate carve-out from the
   * YAML-managed manual-write block (D9), so this shell can't determine eligibility itself and
   * instead shows it optimistically, the same way Edit already does, letting the backend's own
   * permission check be the real gate. Plain Delete no longer exists (D14) — Remove then Purge
   * is the only path to permanently destroying one of these four kinds. */
  onRemove?: () => Promise<void>
  onRevive?: () => Promise<void>
  onPurge?: () => Promise<void>
  /** False for entity kinds with no edit route at all (e.g. Groups, managed via Django admin) — hides the Edit affordance without implying YAML-managed read-only status. Defaults to true. */
  editable?: boolean
  /** True when this entity's kind currently has no active handler: hides Edit and every kind-specific tab, and shows `UnavailableEntityBanner` instead of the usual read-only/conflict banners — identity/metadata/rail fields still render normally. Defaults to false. */
  unavailable?: boolean
  railFields: RailField[]
  links?: LinkOut[]
  /** The fetched entity this canonical detail page renders, or `undefined` while still loading/absent. */
  entity: CatalogEntityUnion | undefined
  /** The full set of installed `entityDetailTab` contributions; the shell filters to the ones whose `when(entity)` applies (docs/plugin-architecture.md:365-380). */
  tabContributions: readonly EntityDetailTabContribution<CatalogEntityUnion>[]
}

/** Core-owned canonical detail shell (ADR 0022): header, action/banner/tab contributions, right rail, shared loading/unavailable/error/permission states. */
export function EntityDetailShell({
  breadcrumb,
  metadata,
  ingestedFrom,
  blockedBy,
  blockedByReason,
  isLoading,
  error,
  editTo,
  onRemove,
  onRevive,
  onPurge,
  editable = true,
  unavailable = false,
  railFields,
  links = [],
  entity,
  tabContributions,
}: EntityDetailShellProps) {
  const navigate = useNavigate()
  // catalog-web-ui spec's "Read-only session sees no detail-page write actions" — applies on
  // top of (not instead of) the existing manual/YAML-managed `isManual` distinction below, and
  // even when the session is also an admin.
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const [searchParams, setSearchParams] = useSearchParams()
  const [isRemoving, setIsRemoving] = useState(false)
  const [isReviving, setIsReviving] = useState(false)
  const [isPurging, setIsPurging] = useState(false)
  const { confirm: confirmRemove, dialogProps: removeDialogProps } = useConfirm()
  const { confirm: confirmPurge, dialogProps: purgeDialogProps } = useConfirm()

  const tabs = entity && !unavailable
    ? tabContributions
        .filter((contribution) => contribution.when(entity))
        .map((contribution) => ({
          value: contribution.value,
          label: contribution.label,
          fullWidth: contribution.fullWidth,
          content: (
            <ContributionBoundary label={contribution.label}>
              <contribution.component entity={entity} />
            </ContributionBoundary>
          ),
        }))
    : []

  const requestedTab = searchParams.get('tab')
  const activeTab = requestedTab && tabs.some((tab) => tab.value === requestedTab) ? requestedTab : (tabs[0]?.value ?? '')
  const activeTabDefinition = tabs.find((tab) => tab.value === activeTab)

  if (isLoading && !metadata) return <Loader size="l" />
  if (error) return <Alert theme="danger" message={error.message} />
  if (!metadata) return null

  const isManual = editable && !ingestedFrom && !unavailable
  // Group has no `status` field (it never leaves `active` — D10 scope) — `'status' in entity`
  // narrows `CatalogEntityUnion` to the four kinds that do, mirroring `isSystem`/`isComponent`-
  // style guards elsewhere rather than widening `GroupEntity` with a field it'll never use.
  const status = entity && 'status' in entity ? entity.status : null
  // Server-computed per-user permissions; an entity without them (older payloads, kinds that
  // don't report them yet) falls back to showing the action and letting the backend answer 403.
  const permissions = entity && 'permissions' in entity ? entity.permissions : null
  const mayEdit = permissions?.canEdit ?? true
  const mayPurge = permissions?.canPurge ?? true
  const canEdit = isManual && !isReadOnly && mayEdit
  const canRemove = isManual && Boolean(onRemove) && status === 'active' && !isReadOnly && mayEdit
  const canRevive = isManual && Boolean(onRevive) && status === 'removed' && !isReadOnly && mayEdit
  // Purge is shown whenever the entity is `removed`, independent of `isManual` — a Purge Grant
  // authorizes Purge on a YAML-managed entity despite the manual-write block (D9), so gating
  // visibility on `isManual` would hide it from exactly the grant holders it exists for.
  const canPurge = !unavailable && Boolean(onPurge) && status === 'removed' && !isReadOnly && mayPurge

  async function handleRemove() {
    if (!onRemove) return
    if (!(await confirmRemove({ title: 'Remove', message: `Remove "${metadata!.name}"? It can be revived later.`, preset: 'default' }))) return
    setIsRemoving(true)
    try {
      await onRemove()
    } finally {
      setIsRemoving(false)
    }
  }

  async function handleRevive() {
    if (!onRevive) return
    setIsReviving(true)
    try {
      await onRevive()
    } finally {
      setIsReviving(false)
    }
  }

  async function handlePurge() {
    if (!onPurge) return
    if (!(await confirmPurge({ title: 'Purge', message: `Purge "${metadata!.name}"? This permanently deletes it and cannot be undone.`, preset: 'danger' }))) return
    setIsPurging(true)
    try {
      await onPurge()
      navigate(breadcrumb.to)
    } finally {
      setIsPurging(false)
    }
  }

  return (
    <div>
      <Breadcrumbs>
        <Breadcrumbs.Item
          href={breadcrumb.to}
          onClick={(event) => {
            event.preventDefault()
            navigate(breadcrumb.to)
          }}
        >
          {breadcrumb.label}
        </Breadcrumbs.Item>
        <Breadcrumbs.Item>{metadata.title || metadata.name}</Breadcrumbs.Item>
      </Breadcrumbs>

      <HeaderActionRow
        left={
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text variant="header-1">{metadata.title || metadata.name}</Text>
              {status === 'removed' && <Label theme="warning">Removed</Label>}
            </div>
            <div style={{ margin: '8px 0' }}>
              <MarkdownDescription text={metadata.description} />
            </div>
            {metadata.tags.length > 0 && <div style={{ marginTop: 8 }}><TagLabels tags={metadata.tags} tagColors={metadata.tagColors} /></div>}
          </div>
        }
        right={
          canEdit || canPurge ? (
            <ContributionBoundary label="Actions">
              <div style={{ display: 'flex', gap: 8 }}>
                {canEdit && (
                  <Button view="outlined" onClick={() => navigate(editTo)}>
                    Edit
                  </Button>
                )}
                {canRemove && (
                  <Button view="outlined" loading={isRemoving} onClick={() => void handleRemove()}>
                    Remove
                  </Button>
                )}
                {canRevive && (
                  <Button view="outlined" loading={isReviving} onClick={() => void handleRevive()}>
                    Revive
                  </Button>
                )}
                {canPurge && (
                  <Button view="outlined-danger" loading={isPurging} onClick={() => void handlePurge()}>
                    Purge
                  </Button>
                )}
              </div>
            </ContributionBoundary>
          ) : null
        }
      />

      {unavailable ? (
        <div style={{ marginBottom: 16 }}>
          <ContributionBoundary label="Unavailable banner">
            <UnavailableEntityBanner />
          </ContributionBoundary>
        </div>
      ) : (
        !isManual && ingestedFrom && (
          <div style={{ marginBottom: 16 }}>
            <ContributionBoundary label="Read-only banner">
              <ReadOnlyBanner ingestedFrom={ingestedFrom} />
            </ContributionBoundary>
          </div>
        )
      )}

      {blockedBy && (
        <div style={{ marginBottom: 16 }}>
          <ContributionBoundary label="Conflict banner">
            <ConflictBanner blockedBy={blockedBy} reason={blockedByReason} />
          </ContributionBoundary>
        </div>
      )}

      <TabProvider value={activeTab} onUpdate={(tab) => {
        const next = new URLSearchParams(searchParams)
        next.set('tab', tab)
        setSearchParams(next)
      }}>
        <TabList>
          {tabs.map((tab) => (
            <Tab key={tab.value} value={tab.value}>
              {tab.label}
            </Tab>
          ))}
        </TabList>

        {activeTabDefinition?.fullWidth ? (
          tabs.map((tab) => (
            <TabPanel key={tab.value} value={tab.value}>
              <div style={{ paddingTop: 16 }}>{tab.content}</div>
            </TabPanel>
          ))
        ) : (
          <div style={{ display: 'flex', gap: 32 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              {tabs.map((tab) => (
                <TabPanel key={tab.value} value={tab.value}>
                  <div style={{ paddingTop: 16 }}>{tab.content}</div>
                </TabPanel>
              ))}
            </div>

            <aside style={{ width: 320, flexShrink: 0, paddingTop: 16 }}>
              <Text variant="subheader-2">About</Text>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                {railFields.map((field) => (
                  <div key={field.label}>
                    <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>
                      {field.label}
                    </Text>
                    <div>{field.value}</div>
                  </div>
                ))}
              </div>
              <LinksRail links={links} />
            </aside>
          </div>
        )}
      </TabProvider>
      <ConfirmDialog {...removeDialogProps} />
      <ConfirmDialog {...purgeDialogProps} />
    </div>
  )
}
