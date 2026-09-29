## Context

The Flow form currently keeps `steps` as JSON text in Monaco, derives a parsed array for a live read-only `FlowGraph` preview, and sends that array unchanged to the existing Flow API. The catalog already exposes `TargetRefSelect`, a searchable grouped lookup that returns canonical `kind:name` references. The backend validates unique step ids, resolved entity refs, valid targets, and a divergence-only tree; it rejects reconverging branches.

The proposed editor must lower the cost of authoring the same persisted JSON structure without making raw JSON unavailable or changing its server contract.

## Goals / Non-Goals

**Goals:**

- Give Flow authors a visual, form-based way to edit every supported step field and transition.
- Keep Visual and JSON modes synchronized through one canonical in-memory `FlowStep[]` representation.
- Reuse the catalog's searchable, grouped reference lookup for optional `entity_ref` values.
- Prevent or clearly explain invalid tree edits before save while retaining server-side validation as the authority.
- Preserve the existing live Flow graph, documentation editor, API payload, and persisted data.

**Non-Goals:**

- Drag-and-drop graph editing, free-form node placement, or a new graph-layout engine.
- Changing the Flow API, database schema, `steps` JSON grammar, or backend validation rules.
- Supporting cycles or branch reconvergence.
- Replacing Monaco or removing direct JSON editing.

## Decisions

### 1. Use a canonical structured steps state with JSON as a serialization view

The form will own a validated `FlowStep[]` value for Visual mode and derive formatted JSON from it. Entering Visual mode parses the current JSON first; if parsing or schema validation fails, the application remains in JSON mode and explains that the JSON must be corrected before switching. Entering JSON mode serializes the current structured value with stable indentation.

This avoids two independently editable sources of truth and ensures a mode switch cannot silently discard work. An alternative of synchronizing two mutable values on every keystroke would make invalid/transient JSON and merge conflicts difficult to reason about.

### 2. Use ordered step cards plus explicit transition controls

Visual mode will render steps in array order as editable cards. A card exposes its id, title, optional summary, optional catalog entity, and outgoing transition controls. A single transition is represented as `next_step`; branches are represented as editable `next_steps` rows with a target selector and optional label. Users can add, remove, and reorder cards and add or remove branch rows.

This is visual authoring without the interaction and accessibility risks of a drag-and-drop canvas. The existing `FlowGraph` remains the spatial preview of the resulting tree. The alternative of editing connections directly on the graph is deferred: it would require pointer, keyboard, focus, hit-testing, and layout semantics beyond the current read-only graph implementation.

### 3. Reuse the existing typed catalog lookup

The visual card will use the existing grouped, filterable `TargetRefSelect` behavior for `entity_ref`, displaying the entity kind and submitting the canonical ref. This gives users lookup across Systems, Components, APIs, Resources, Users, and Groups while reusing the catalog's pagination/listing mechanisms. JSON mode continues to allow any backend-supported canonical reference, with backend validation remaining final.

### 4. Validate structural changes locally and preserve the backend as authority

The visual editor will prevent a transition target from being selected more than once, disallow targets that do not exist, and report duplicate/empty IDs. It will avoid introducing a cycle when choosing a target. Save remains blocked while local errors exist; the existing backend response is still shown for race conditions or catalog changes after lookup.

Local validation deliberately mirrors the backend's strict-tree invariants rather than trying to infer a richer graph model. The backend remains the source of truth for persisted data.

### 5. Make the mode switch a compact settings action in the Steps header

The Steps header will expose a gear/settings-style control with Visual and JSON choices, analogous to the Markdown editor's mode selection. The Add Step action stays available in both modes and operates on the canonical data: it creates a unique, unconnected step and focuses the new visual card or selects the corresponding JSON block.

This preserves discoverability and keeps the primary editing surface uncluttered. Two permanent tabs were considered but would use space and imply that the modes are independent views rather than alternate editing surfaces.

## Risks / Trade-offs

- [A JSON document can be syntactically valid yet violate the step schema] → Require JSON/schema validation before Visual mode and preserve the JSON editor with its existing diagnostics.
- [The current lookup fetches a bounded list per entity kind] → Reuse it for the first implementation; record server-side search/pagination as a follow-up only if catalog sizes make lookup incomplete.
- [A visual editor may omit unfamiliar future JSON fields] → Preserve unknown step fields through structured mutations where feasible; until that is supported, prevent a mode switch if the parser encounters unsupported shape and direct the user to JSON mode.
- [Client and server validation may drift] → Keep server validation unchanged and cover the shared expected invariants with frontend tests.
- [Graph rendering can lag mutations because it is debounced] → Treat cards as the immediate source of editing feedback and retain the graph's current last-good rendering behavior.

## Migration Plan

No data migration is required: persisted Flow `steps` remain the same JSON array. Deploying the frontend adds an alternate editor only. Rollback consists of removing the visual mode; existing and newly saved Flow data remain editable in the JSON editor.

## Open Questions

- The first release will use form controls for transitions. Drag-to-connect graph editing can be evaluated later after observing author workflows.
- The lookup currently includes all architecture-reference kinds. Product validation may later narrow the allowed kinds for Flow steps, but no restriction is introduced in this change.
