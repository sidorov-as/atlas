// JSON Schema for the `steps` array edited in FlowFormPage's Monaco editor.
// Mirrors the `FlowStep` type in `flowLayout.ts` structurally; it validates
// shape only — `entity_ref` resolvability and the
// acyclic-transition-graph rule (unknown targets, cycles; reconvergence is
// allowed) are checked separately, by
// `validateFlowSteps` client-side and `validate_steps` server-side.

import { GRAVITY_ICON_NAMES } from './gravityIcons'

export const FLOW_STEP_SCHEMA_URI = 'https://atlas.internal/schemas/flow-steps.json'

/** Every 2-of-N combination of `fieldSchemas`' keys, each as a `{properties, required}` fragment — the building block for a step's "at most one ref field" `not`/`anyOf` exclusion below. */
function mutuallyExclusiveRefFieldPairs(fieldSchemas: Record<string, unknown>): unknown[] {
  const names = Object.keys(fieldSchemas)
  const pairs: unknown[] = []
  for (let i = 0; i < names.length; i += 1) {
    for (let j = i + 1; j < names.length; j += 1) {
      const [a, b] = [names[i], names[j]]
      pairs.push({ properties: { [a]: fieldSchemas[a], [b]: fieldSchemas[b] }, required: [a, b] })
    }
  }
  return pairs
}

const transitionSchema = {
  type: 'object',
  properties: {
    id: { type: 'string', description: 'Target step id' },
    label: { type: 'string', description: 'Transition label (optional)' },
  },
  required: ['id'],
  additionalProperties: false,
}

const positionSchema = {
  type: 'object',
  properties: {
    x: { type: 'number' },
    y: { type: 'number' },
  },
  required: ['x', 'y'],
  additionalProperties: false,
  description: 'Manually placed canvas position (optional); steps without one autolayout via ELK',
  errorMessage: "Invalid position: expected {'x': number, 'y': number}",
}

const LABEL_THEMES = ['success', 'danger', 'warning', 'info', 'utility', 'normal']
// `color` shares `label_theme`'s six-name vocabulary
// (`flowNodePalette.ts`'s `FlowNodeTheme`); kept as a distinct constant (not a
// reused reference to `LABEL_THEMES`) since the two fields' allowed sets are
// only coincidentally identical today, not definitionally the same.
const STEP_COLORS = ['success', 'danger', 'warning', 'info', 'utility', 'normal']

// Mirrors `apps/catalog/models/flow.py`'s `QUERY_REF_KEYS`/`EVENT_REF_KEYS`
// a point-in-time
// snapshot, not re-derived from the referenced Endpoint/Operation. `summary`
// mirrors `REF_OPTIONAL_KEYS` — optional, empty string allowed, since the source
// Endpoint's/Operation's own `summary` is itself optional; feeds the Call/
// Event node's card subtitle.
const queryRefSchema = {
  type: 'object',
  properties: {
    api: { type: 'string', minLength: 1, description: 'Owning API ref, e.g. api:orders-api' },
    endpoint: { type: 'string', minLength: 1, description: 'Endpoint id (UUID)' },
    method: { type: 'string', minLength: 1, description: 'Snapshotted HTTP method' },
    path: { type: 'string', minLength: 1, description: 'Snapshotted path' },
    summary: { type: 'string', description: "Snapshotted Endpoint summary (optional); feeds the node's subtitle" },
  },
  required: ['api', 'endpoint', 'method', 'path'],
  additionalProperties: false,
}

const eventRefSchema = {
  type: 'object',
  properties: {
    api: { type: 'string', minLength: 1, description: 'Owning API ref, e.g. api:orders-api' },
    operation: { type: 'string', minLength: 1, description: 'Operation id (UUID)' },
    direction: { type: 'string', minLength: 1, description: "Snapshotted direction, e.g. 'send'/'receive'" },
    channel: { type: 'string', minLength: 1, description: 'Snapshotted channel address' },
    summary: { type: 'string', description: "Snapshotted Operation summary (optional); feeds the node's subtitle" },
  },
  required: ['api', 'operation', 'direction', 'channel'],
  additionalProperties: false,
}

export const flowStepSchema = {
  type: 'array',
  items: {
    type: 'object',
    properties: {
      id: { type: 'string', description: 'Unique step identifier' },
      title: { type: 'string', description: 'Display title (optional)' },
      summary: { type: 'string', description: 'Short description (optional)' },
      entity_ref: {
        type: ['string', 'null'],
        description: 'Reference to a system/component/resource/api (optional)',
      },
      next_step: {
        anyOf: [transitionSchema, { type: 'null' }],
        description: 'Single next transition (optional)',
      },
      next_steps: {
        type: 'array',
        items: transitionSchema,
        description: 'Multiple next transitions (optional)',
      },
      position: positionSchema,
      label_theme: {
        type: 'string',
        enum: LABEL_THEMES,
        description: "Deprecated: replaced by 'color'. Still accepted so an unmigrated flow keeps validating (optional)",
        errorMessage: `Invalid label_theme: expected one of ${LABEL_THEMES.join(', ')}`,
      },
      color: {
        type: 'string',
        enum: STEP_COLORS,
        description: "Plain Step node color, e.g. 'success'/'danger' (optional)",
        errorMessage: `Invalid color: expected one of ${STEP_COLORS.join(', ')}`,
      },
      icon: {
        type: 'string',
        enum: GRAVITY_ICON_NAMES,
        description: 'Plain Step node icon, a @gravity-ui/icons component name (optional)',
        errorMessage: 'Invalid icon: expected a known @gravity-ui/icons component name',
      },
      type_label: {
        type: 'string',
        description: 'Plain Step node chip label; free text, falls back to "Step" when blank/unset (optional)',
      },
      external_label: {
        type: 'string',
        description: 'Out-of-catalog reference label; mutually exclusive with entity_ref, query_ref, and event_ref (optional)',
      },
      query_ref: {
        anyOf: [queryRefSchema, { type: 'null' }],
        description: 'Endpoint reference snapshot (Query step); mutually exclusive with entity_ref, external_label, and event_ref (optional)',
      },
      event_ref: {
        anyOf: [eventRefSchema, { type: 'null' }],
        description: 'Operation reference snapshot (Event step); mutually exclusive with entity_ref, external_label, and query_ref (optional)',
      },
      flow_ref: {
        type: ['number', 'null'],
        description: 'Reference to another Flow by id (Flow step); mutually exclusive with every other ref field (optional)',
      },
      link_url: {
        type: ['string', 'null'],
        description: 'External URL (Link step); mutually exclusive with every other ref field (optional)',
      },
    },
    required: ['id'],
    additionalProperties: false,
    // A step cannot carry more than one of entity_ref/external_label/
    // query_ref/event_ref/flow_ref/link_url. Generated (not hand-
    // enumerated) once the six-way extension made this C(6,2) = 15 pairs
    // rather than the original C(4,2) = 6. Nested in `allOf` (rather than a
    // bare top-level `not`) so its `errorMessage` doesn't also get read for
    // this schema's own `type`/`additionalProperties` violations —
    // vscode-json-languageservice reads `schema.errorMessage` off whichever
    // schema object failed, and those keywords live on the same object as
    // `not` would.
    allOf: [
      {
        not: {
          anyOf: mutuallyExclusiveRefFieldPairs({
            entity_ref: { type: 'string', minLength: 1 },
            external_label: { type: 'string', minLength: 1 },
            query_ref: queryRefSchema,
            event_ref: eventRefSchema,
            flow_ref: { type: 'number' },
            link_url: { type: 'string', minLength: 1 },
          }),
        },
        errorMessage: 'A step cannot have more than one of entity_ref, external_label, query_ref, event_ref, flow_ref, link_url',
      },
    ],
  },
}
