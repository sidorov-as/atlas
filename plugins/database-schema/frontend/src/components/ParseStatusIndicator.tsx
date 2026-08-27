// Visible parse-failure indicator (a bad edit is saved as-is,
// never silently dropped, so the failure has to stay visible on the editor).
import { Label, Tooltip } from '@gravity-ui/uikit'
import type { ParseStatus } from '../lib/databaseSchemaApi'

export function ParseStatusIndicator({ status }: { status: ParseStatus }) {
  if (status === 'ok') return null
  return (
    <Tooltip
      content="This SQL could not be parsed. Your text is still saved, but no ER Diagram can be rendered from it."
      placement="top"
    >
      <Label theme="danger">Parse failed</Label>
    </Tooltip>
  )
}
