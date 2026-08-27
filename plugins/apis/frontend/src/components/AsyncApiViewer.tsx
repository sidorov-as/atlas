// Split from ApiSpecDocViewer so an AsyncAPI doc never pulls in the OpenAPI
// renderer's bundle at all, and vice versa.
//
// @asyncapi/react-component's Avro schema parser (avsc) assumes Node's
// Buffer/process/util globals; vite.config.ts's nodePolyfills plugin supplies them.
import AsyncApiComponent from '@asyncapi/react-component'
import '@asyncapi/react-component/styles/default.min.css'

export default function AsyncApiViewer({ schema }: { schema: object }) {
  return <AsyncApiComponent schema={schema} />
}
