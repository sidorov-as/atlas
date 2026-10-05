// Shared builders for this plugin's endpoint-detail and operation-detail test
// suites —
// kept out of `src/**/*.test.tsx` so vitest doesn't pick this up as a spec.
import type { ApiEntity } from 'frontend/lib/types'
import type {
  Endpoint,
  EndpointConsumers,
  Operation,
  OperationConsumerParticipant,
  OperationConsumers,
  OperationMessage,
  OperationService,
  ServiceSummary,
} from './lib/types'

export function makeEndpoint(overrides: Partial<Endpoint> = {}): Endpoint {
  return {
    id: 'endpoint-1',
    apiId: 'api-1',
    method: 'GET',
    path: '/v1/invoices',
    operationId: 'listInvoices',
    summary: 'List invoices',
    description: '',
    deprecated: false,
    tags: [],
    request: { parameters: [], body: null },
    responses: [],
    externalDocs: null,
    security: [],
    status: 'active',
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeApi(overrides: Partial<ApiEntity['spec']> = {}): ApiEntity {
  return {
    id: 'api-1',
    apiVersion: 'atlas/v1alpha1',
    kind: 'API',
    metadata: {
      name: 'billing-api',
      title: '',
      description: '',
      documentation: '',
      labels: {},
      tags: [],
      tagColors: {},
      links: [],
    },
    spec: {
      type: 'openapi',
      owner: 'group:platform',
      ownerId: 'group-1',
      system: 'system:core',
      systemId: 'system-1',
      specSource: 'none',
      specUrl: '',
      specContent: '',
      specResolvedAt: null,
      specResolveFailed: false,
      endpointsSyncedAt: null,
      endpointsSyncFailed: false,
      operationsSyncedAt: null,
      operationsSyncFailed: false,
      resolvedBaseUrl: '',
      resolvedProtocol: '',
      ...overrides,
    },
    status: 'active',
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: [],
  }
}

export function makeServiceSummary(overrides: Partial<ServiceSummary> = {}): ServiceSummary {
  return {
    id: 'service-1',
    ref: 'component:billing-service',
    name: 'billing-service',
    title: '',
    team: 'group:platform',
    teamId: 'group-1',
    teamName: 'platform',
    system: 'system:default/core',
    systemId: 'system-1',
    systemName: 'core',
    ...overrides,
  }
}

export function makeConsumers(services: ServiceSummary[] = [], endpointOverrides: Partial<EndpointConsumers['endpoint']> = {}): EndpointConsumers {
  return {
    endpoint: { id: 'endpoint-1', method: 'GET', path: '/v1/invoices', status: 'active', ...endpointOverrides },
    services,
    count: services.length,
  }
}

export function makeOperation(overrides: Partial<Operation> = {}): Operation {
  return {
    id: 'operation-1',
    apiId: 'api-1',
    channelAddress: 'booking.created',
    channelProtocol: 'kafka',
    direction: 'send',
    operationKey: 'onBookingCreated',
    operationId: 'onBookingCreated',
    summary: 'A booking was created',
    description: '',
    tags: [],
    messages: [],
    externalDocs: null,
    status: 'active',
    deprecated: false,
    provider: null,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeOperationMessage(overrides: Partial<OperationMessage> = {}): OperationMessage {
  return {
    name: 'BookingCreated',
    title: '',
    summary: '',
    contentType: '',
    schema: null,
    example: null,
    headers: null,
    ...overrides,
  }
}

export function makeOperationService(overrides: Partial<OperationService> = {}): OperationService {
  return {
    id: 'usage-1',
    service: makeServiceSummary(),
    role: 'subscriber',
    linkedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeOperationConsumers(
  participants: OperationConsumerParticipant[] = [],
  operationOverrides: Partial<OperationConsumers['operation']> = {},
): OperationConsumers {
  return {
    operation: {
      id: 'operation-1',
      channelAddress: 'booking.created',
      channelProtocol: 'kafka',
      direction: 'send',
      status: 'active',
      ...operationOverrides,
    },
    participants,
    count: participants.length,
    publisherCount: participants.filter((participant) => participant.role === 'publisher').length,
    subscriberCount: participants.filter((participant) => participant.role === 'subscriber').length,
  }
}
