// Split from ApiSpecDocViewer so an OpenAPI doc never pulls in the AsyncAPI
// renderer's bundle (and its Node-only dependencies) at all, and vice versa.
import { RedocStandalone } from 'redoc'

export default function OpenApiViewer({ spec }: { spec: object }) {
  return <RedocStandalone spec={spec} />
}
