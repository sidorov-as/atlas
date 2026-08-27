import { useState } from 'react'
import { ClipboardButton, Label, Select, Text } from '@gravity-ui/uikit'
import { EntityTable } from 'frontend/components/EntityTable'
import { EndpointSchemaViewer } from './EndpointSchemaViewer'
import { statusCodeTheme } from '../lib/badges'
import type { Endpoint, EndpointResponseHeader } from '../lib/types'

const CODE_BLOCK_STYLE = { background: 'var(--g-color-base-generic)', padding: 12, borderRadius: 8, overflow: 'auto' } as const

/** Defaults to the first `2xx` response, falling back to the first response otherwise (spec's Response tab default-selection scenarios). */
function defaultStatusCode(responses: Endpoint['responses']): string | null {
  const first2xx = responses.find((response) => /^2\d\d$/.test(response.statusCode))
  return (first2xx ?? responses[0])?.statusCode ?? null
}

/** Response tab: a status selector plus that response's content type, schema, and example with a copy action. */
export function EndpointResponseTab({ endpoint }: { endpoint: Endpoint }) {
  const [selected, setSelected] = useState(() => defaultStatusCode(endpoint.responses))

  if (endpoint.responses.length === 0) {
    return <Text color="secondary">No responses documented</Text>
  }

  const response = endpoint.responses.find((item) => item.statusCode === selected) ?? endpoint.responses[0]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Select
        value={[response.statusCode]}
        onUpdate={(value) => setSelected(value[0] ?? null)}
        options={endpoint.responses.map((item) => ({ value: item.statusCode, content: item.statusCode }))}
        width={160}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Label theme={statusCodeTheme(response.statusCode)}>{response.statusCode}</Label>
        {response.contentType && <Text color="secondary">{response.contentType}</Text>}
      </div>
      {response.description && <Text>{response.description}</Text>}
      <section>
        <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>Schema</Text>
        <EndpointSchemaViewer schema={response.schema} />
      </section>
      {Object.keys(response.headers).length > 0 && (
        <section>
          <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>Headers</Text>
          <EntityTable
            data={Object.entries(response.headers).map(([name, header]) => ({ name, ...header }))}
            columns={[
              { id: 'name', name: 'Name', width: 220, template: (item: { name: string } & EndpointResponseHeader) => <code>{item.name}</code> },
              { id: 'type', name: 'Type', width: 160, template: (item: { name: string } & EndpointResponseHeader) => item.schema?.type ?? '—' },
              { id: 'description', name: 'Description', template: (item: { name: string } & EndpointResponseHeader) => item.description || '—' },
            ]}
            getRowId={(item: { name: string } & EndpointResponseHeader) => item.name}
          />
        </section>
      )}
      {response.example != null && (
        <section>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <Text variant="subheader-2">Example</Text>
            <ClipboardButton text={JSON.stringify(response.example, null, 2)} size="s" />
          </div>
          <pre style={CODE_BLOCK_STYLE}>{JSON.stringify(response.example, null, 2)}</pre>
        </section>
      )}
    </div>
  )
}
