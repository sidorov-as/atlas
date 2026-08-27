import { useState } from 'react'
import { ClipboardButton, SegmentedRadioGroup, Text } from '@gravity-ui/uikit'
import { EndpointSchemaViewer } from './EndpointSchemaViewer'
import type { Operation } from '../lib/types'

const CODE_BLOCK_STYLE = { background: 'var(--g-color-base-generic)', padding: 12, borderRadius: 8, overflow: 'auto' } as const

/** Message tab: a selector when the channel carries more than one message shape (spec's "Operation with multiple message shapes" scenario), then that message's schema/example — reuses `EndpointSchemaViewer`'s type support. */
export function OperationMessageTab({ operation }: { operation: Operation }) {
  const messages = operation.messages
  const [selectedIndex, setSelectedIndex] = useState(0)
  const message = messages[selectedIndex]

  if (!message) {
    return <Text color="secondary">No message documented</Text>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {messages.length > 1 && (
        <SegmentedRadioGroup
          value={String(selectedIndex)}
          onUpdate={(value) => setSelectedIndex(Number(value))}
          options={messages.map((item, index) => ({
            value: String(index),
            content: item.title || item.name || `Message ${index + 1}`,
          }))}
        />
      )}

      {message.summary && <Text color="secondary">{message.summary}</Text>}

      <section>
        <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>
          Payload{message.contentType ? ` (${message.contentType})` : ''}
        </Text>
        <EndpointSchemaViewer schema={message.schema} />
      </section>

      {message.headers && (
        <section>
          <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>Headers</Text>
          <EndpointSchemaViewer schema={message.headers} />
        </section>
      )}

      {message.example != null && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <Text color="secondary">Example</Text>
            <ClipboardButton text={JSON.stringify(message.example, null, 2)} size="s" />
          </div>
          <pre style={CODE_BLOCK_STYLE}>{JSON.stringify(message.example, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
