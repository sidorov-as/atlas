import {
  ArrowsRotateRight,
  Book,
  Bucket,
  Code,
  Cube,
  Database,
  Envelope,
  GraphNode,
  Globe,
  PlugConnection,
  Server,
  Shield,
  Thunderbolt,
} from '@gravity-ui/icons'
import type { IconData } from '@gravity-ui/uikit'

/** Icon shown next to an owner (Group) reference, e.g. list-page Owner columns and detail-page rails. */
export const OwnerIcon = Shield

const COMPONENT_TYPE_ICONS: Record<string, IconData> = {
  service: Cube,
  website: Globe,
  library: Book,
  worker: ArrowsRotateRight,
}

const RESOURCE_TYPE_ICONS: Record<string, IconData> = {
  database: Database,
  cache: Thunderbolt,
  bucket: Bucket,
  queue: Envelope,
  cluster: Server,
}

const API_TYPE_ICONS: Record<string, IconData> = {
  openapi: Code,
  grpc: PlugConnection,
  asyncapi: Envelope,
  graphql: GraphNode,
}

export const componentTypeIcon = (type: string): IconData => COMPONENT_TYPE_ICONS[type] ?? Cube
export const resourceTypeIcon = (type: string): IconData => RESOURCE_TYPE_ICONS[type] ?? Database
export const apiTypeIcon = (type: string): IconData => API_TYPE_ICONS[type] ?? PlugConnection
