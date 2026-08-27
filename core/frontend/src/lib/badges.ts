import type { LabelProps } from '@gravity-ui/uikit'

export const LIFECYCLE_THEME: Record<string, LabelProps['theme']> = {
  production: 'success',
  experimental: 'warning',
  deprecated: 'unknown',
}

export const COMPONENT_TYPE_THEME: Record<string, LabelProps['theme']> = {
  service: 'info',
  website: 'utility',
  library: 'normal',
  worker: 'clear',
}

export const RESOURCE_TYPE_THEME: Record<string, LabelProps['theme']> = {
  database: 'success',
  cache: 'utility',
  bucket: 'normal',
  queue: 'clear',
  cluster: 'danger',
}

export const API_TYPE_THEME: Record<string, LabelProps['theme']> = {
  openapi: 'info',
  grpc: 'utility',
  asyncapi: 'normal',
  graphql: 'clear',
}
