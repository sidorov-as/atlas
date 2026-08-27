import { useState } from 'react'
import { Icon, Text } from '@gravity-ui/uikit'
import { ChevronDown, ChevronRight } from '@gravity-ui/icons'
import type { EndpointSchema } from '../lib/types'

function typeLabel(schema: EndpointSchema): string {
  if (schema['$ref']) {
    const parts = schema['$ref'].split('/')
    return parts[parts.length - 1] || schema['$ref']
  }
  let label = schema.type ?? 'any'
  if (schema.type === 'array') label = `array<${schema.items ? typeLabel(schema.items) : 'any'}>`
  if (schema.format) label += `(${schema.format})`
  if (schema.nullable) label += ' | null'
  return label
}

/** The nested schema that owns `properties`/`required` to expand for a node: itself for `object`, its `items` for `array`. */
function objectSchema(schema: EndpointSchema): EndpointSchema | null {
  if (schema.type === 'object') return schema
  if (schema.type === 'array' && schema.items?.type === 'object') return schema.items
  return null
}

function SchemaNode({ name, schema, required, depth }: { name?: string; schema: EndpointSchema; required?: boolean; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const nested = objectSchema(schema)
  const properties = nested ? Object.entries(nested.properties) : []
  const requiredSet = new Set(nested?.required ?? [])
  const isExpandable = properties.length > 0

  return (
    <div style={{ marginLeft: depth ? 16 : 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0' }}>
        {isExpandable ? (
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex', color: 'inherit' }}
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            <Icon data={expanded ? ChevronDown : ChevronRight} size={14} />
          </button>
        ) : (
          <span style={{ width: 14, display: 'inline-block' }} />
        )}
        {name && <Text variant="code-2">{name}</Text>}
        <Text color="secondary" variant="code-2">{typeLabel(schema)}</Text>
        {required && <Text color="danger" variant="caption-2">required</Text>}
        {schema.enum && <Text color="secondary" variant="caption-2">enum: {schema.enum.join(', ')}</Text>}
      </div>
      {schema.description && (
        <Text color="secondary" style={{ display: 'block', marginLeft: 20 }}>{schema.description}</Text>
      )}
      {isExpandable && expanded && (
        <div>
          {properties.map(([propName, propSchema]) => (
            <SchemaNode key={propName} name={propName} schema={propSchema} required={requiredSet.has(propName)} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

/** Recursive schema tree for the Request/Response tabs — object/array/string/integer/number/boolean, `enum`, `nullable`, `$ref`, with expandable/collapsible nested objects. */
export function EndpointSchemaViewer({ schema }: { schema: EndpointSchema | null | undefined }) {
  if (!schema) return <Text color="secondary">No schema</Text>
  return <SchemaNode schema={schema} depth={0} />
}
