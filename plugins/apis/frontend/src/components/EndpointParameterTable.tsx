import { Label, Text } from '@gravity-ui/uikit'
import { EntityTable } from 'frontend/components/EntityTable'
import type { EndpointParameter } from '../lib/types'

/** `string (uuid)` when `format` is present, `string` otherwise — spec's "Parameter with a format shows type and format together" scenario. */
function formatParameterType(schema: EndpointParameter['schema']): string {
  if (!schema?.type) return '—'
  return schema.format ? `${schema.type} (${schema.format})` : schema.type
}

/** Path/query/header parameter table — omitted entirely when `parameters` is empty (spec's "Endpoint with no parameters" scenario), shared by the Overview and Request tabs. */
export function EndpointParameterTable({ title, parameters }: { title: string; parameters: EndpointParameter[] }) {
  if (parameters.length === 0) return null
  return (
    <section>
      <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>{title}</Text>
      <EntityTable
        data={parameters}
        columns={[
          { id: 'name', name: 'Name', width: 220, template: (item: EndpointParameter) => <code>{item.name}</code> },
          {
            id: 'required',
            name: 'Required',
            width: 110,
            template: (item: EndpointParameter) => (
              <Label theme={item.required ? 'success' : 'info'}>{item.required ? 'Yes' : 'No'}</Label>
            ),
          },
          {
            id: 'type',
            name: 'Type',
            width: 200,
            template: (item: EndpointParameter) => (
              <div>
                <div>{formatParameterType(item.schema)}</div>
                {item.schema?.enum && item.schema.enum.length > 0 && (
                  <Text color="secondary" variant="caption-2" style={{ display: 'block' }}>
                    Allowed: {item.schema.enum.join(', ')}
                  </Text>
                )}
              </div>
            ),
          },
          { id: 'description', name: 'Description', template: (item: EndpointParameter) => item.description || '—' },
        ]}
        getRowId={(item: EndpointParameter) => `${item.location}-${item.name}`}
      />
    </section>
  )
}
