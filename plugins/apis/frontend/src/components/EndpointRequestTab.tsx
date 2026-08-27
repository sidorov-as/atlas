import { ClipboardButton, Text } from '@gravity-ui/uikit'
import { EndpointParameterTable } from './EndpointParameterTable'
import { EndpointSchemaViewer } from './EndpointSchemaViewer'
import type { Endpoint } from '../lib/types'

const CODE_BLOCK_STYLE = { background: 'var(--g-color-base-generic)', padding: 12, borderRadius: 8, overflow: 'auto' } as const

/** Request tab: parameters (grouped by location) plus request body schema/example — omitted entirely when there is no body (spec's "Endpoint with no request body" scenario). */
export function EndpointRequestTab({ endpoint }: { endpoint: Endpoint }) {
  const pathParams = endpoint.request.parameters.filter((parameter) => parameter.location === 'path')
  const queryParams = endpoint.request.parameters.filter((parameter) => parameter.location === 'query')
  const headerParams = endpoint.request.parameters.filter((parameter) => parameter.location === 'header')
  const body = endpoint.request.body

  const hasParameters = pathParams.length > 0 || queryParams.length > 0 || headerParams.length > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <EndpointParameterTable title="Path parameters" parameters={pathParams} />
      <EndpointParameterTable title="Query parameters" parameters={queryParams} />
      <EndpointParameterTable title="Header parameters" parameters={headerParams} />

      {body ? (
        <section>
          <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>
            Request body{body.contentType ? ` (${body.contentType})` : ''}
          </Text>
          <EndpointSchemaViewer schema={body.schema} />
          {body.example != null && (
            <div style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text color="secondary">Example</Text>
                <ClipboardButton text={JSON.stringify(body.example, null, 2)} size="s" />
              </div>
              <pre style={CODE_BLOCK_STYLE}>{JSON.stringify(body.example, null, 2)}</pre>
            </div>
          )}
        </section>
      ) : (
        !hasParameters && <Text color="secondary">No request parameters or body documented</Text>
      )}
    </div>
  )
}
