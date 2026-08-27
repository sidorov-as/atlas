import { Alert, Loader, Text } from '@gravity-ui/uikit'
import { EntityTable } from './EntityTable'
import type { HistoryRecord } from '../lib/types'
import { useAsync } from '../lib/useAsync'

const ACTION_LABELS: Record<HistoryRecord['action'], string> = {
  create: 'Created',
  update: 'Updated',
  delete: 'Deleted',
  remove: 'Removed',
  revive: 'Revived',
  purge: 'Purged',
}

function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString()
}

/** Read-only lifecycle History section (entity-removal-lifecycle spec: "Remove/Revive/Purge are audited and visible on a History tab") — sourced from `EntityAuditRecord`s via `{kind}Api.history(id)`. */
export function HistoryTab({ fetchHistory }: { fetchHistory: () => Promise<HistoryRecord[]> }) {
  const { data: records, error, isLoading } = useAsync(fetchHistory, [])

  if (isLoading && !records) return <Loader size="m" />
  if (error) return <Alert theme="danger" message={error.message} />

  return (
    <EntityTable
      data={records ?? []}
      columns={[
        { id: 'action', name: 'Action', template: (record) => ACTION_LABELS[record.action] },
        {
          id: 'actor',
          name: 'Actor',
          template: (record) => record.actor ?? <Text color="secondary">Ingestion</Text>,
        },
        { id: 'timestamp', name: 'When', template: (record) => formatTimestamp(record.timestamp) },
      ]}
      getRowId={(_record, index) => String(index)}
      emptyMessage="No history yet"
    />
  )
}
