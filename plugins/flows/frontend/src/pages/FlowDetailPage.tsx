import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Alert, Breadcrumbs, Button, Label, Loader, Tab, TabList, TabPanel, TabProvider, Text } from '@gravity-ui/uikit'
import { FlowGraph } from '../components/FlowGraph'
import type { FlowLayoutDirection, FlowLayoutEngine } from '../lib/flowLayout'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { DocumentationPreview } from 'frontend/components/DocumentationPreview'
import { HeaderActionRow } from 'frontend/components/HeaderActionRow'
import { MarkdownDescription } from 'frontend/components/MarkdownDescription'
import { flowsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'
import { refName, type FlowStep, type FlowStepRefStatus } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'

function FlowCanvasPanel({ steps, refStatus, autolayoutEnabled, layoutDirection, layoutEngine }: { steps: FlowStep[], refStatus?: Record<string, FlowStepRefStatus>, autolayoutEnabled: boolean, layoutDirection: FlowLayoutDirection, layoutEngine: FlowLayoutEngine }) {
  const { containerRef, height } = useFillViewportHeight()
  return (
    <div ref={containerRef}>
      <FlowGraph steps={steps} refStatus={refStatus} autolayoutEnabled={autolayoutEnabled} layoutDirection={layoutDirection} layoutEngine={layoutEngine} height={height} />
    </div>
  )
}

/** Flow detail: Overview/Flow tabs, `FlowGraph` render, edit/delete entry points. */
export function FlowDetailPage() {
  const { id } = useParams()
  const flowId = Number(id)
  const navigate = useNavigate()
  // A read-only session sees no Edit/Delete on a Flow detail page —
  // FlowDetailPage is outside EntityDetailShell so it gates itself.
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const { data: flow, error, isLoading } = useAsync(() => flowsApi.get(flowId), [flowId])
  const [isDeleting, setIsDeleting] = useState(false)
  const [searchParams] = useSearchParams()
  // A Flow node's navigate control (`FlowNodes.tsx`) links here with
  // `?tab=flow` so it opens straight on the diagram rather than Overview —
  // read once as the initial tab, same "arrive on the right tab" intent as
  // `FlowFormPage`'s `location.state.fromTab`, but URL-carried since this
  // link always opens in a fresh tab, where router `state` doesn't survive.
  const [activeTab, setActiveTab] = useState(() => (searchParams.get('tab') === 'flow' ? 'flow' : 'overview'))
  const { confirm, dialogProps } = useConfirm()

  if (isLoading && !flow) return <Loader size="l" />
  if (error) return <Alert theme="danger" message={error.message} />
  if (!flow) return null

  async function handleDelete() {
    if (!(await confirm({ title: 'Delete', message: `Delete "${flow!.name}"? This cannot be undone.`, preset: 'danger' }))) return
    setIsDeleting(true)
    try {
      await flowsApi.remove(flow!.id)
      navigate('/flows')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div>
      <Breadcrumbs>
        <Breadcrumbs.Item
          href="/flows"
          onClick={(event) => {
            event.preventDefault()
            navigate('/flows')
          }}
        >
          Flows
        </Breadcrumbs.Item>
        <Breadcrumbs.Item>{flow.name}</Breadcrumbs.Item>
      </Breadcrumbs>

      <HeaderActionRow
        left={
          <div>
            <Text variant="header-1">{flow.name}</Text>
            <div style={{ margin: '8px 0' }}>
              <MarkdownDescription text={flow.description} />
            </div>
          </div>
        }
        right={
          isReadOnly ? null : (
            <div style={{ display: 'flex', gap: 8 }}>
              <Button
                view="outlined"
                onClick={() => navigate(`/flows/${flow.id}/edit`, { state: { fromTab: activeTab } })}
              >
                Edit
              </Button>
              <Button view="outlined-danger" loading={isDeleting} onClick={() => void handleDelete()}>
                Delete
              </Button>
            </div>
          )
        }
      />

      <TabProvider value={activeTab} onUpdate={setActiveTab}>
        <TabList>
          <Tab value="overview">Overview</Tab>
          <Tab value="flow">Flow</Tab>
        </TabList>

        {activeTab === 'flow' ? (
          <TabPanel value="flow">
            <div style={{ paddingTop: 16 }}>
              <FlowCanvasPanel steps={flow.steps} refStatus={flow.refStatus} autolayoutEnabled={flow.autolayoutEnabled} layoutDirection={flow.layoutDirection} layoutEngine={flow.layoutEngine} />
            </div>
          </TabPanel>
        ) : (
          <div style={{ display: 'flex', gap: 32 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <TabPanel value="overview">
                <div style={{ paddingTop: 16 }}>
                  <DocumentationPreview value={flow.documentation} />
                </div>
              </TabPanel>
            </div>

            <aside style={{ width: 260, flexShrink: 0, paddingTop: 16 }}>
              <Text variant="subheader-2">About</Text>
              <div style={{ marginTop: 12 }}>
                <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>
                  System
                </Text>
                <Label>{refName(flow.system)}</Label>
              </div>
            </aside>
          </div>
        )}
      </TabProvider>
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}
