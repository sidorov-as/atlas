## Context

Three sibling vocabularies exist across Atlas today and were developed independently:

- **Components** (`plugins/standard-catalog`): `type` is one of `service | website | library | worker` (`core/frontend/src/lib/types.ts:125`), each with its own icon (`COMPONENT_TYPE_ICONS`, `core/frontend/src/lib/icons.ts:21-26`) and color (`COMPONENT_TYPE_THEME`, `core/frontend/src/lib/badges.ts:9-14`).
- **APIs** (`plugins/apis`): an API is `openapi | grpc | asyncapi | graphql`; an `openapi` API's operations are called Endpoints (`ApiEndpoint`, has `method`/`path`/`operation_id`); an `asyncapi` API's are called Operations (`ApiOperation`, has `channel_address`/`direction`). Both already have Swagger-like colored badges (`METHOD_THEME`/`DIRECTION_THEME`, `plugins/apis/frontend/src/lib/badges.ts:9-17,36-39`).
- **Flow** (`plugins/flows`): `FlowNodeKind` (`plugins/flows/frontend/src/lib/flowNodeKind.ts:18`) is `actor | team | service | data | api | system | external | step | query | event`, computed per step by `flowNodeKindOf` from whichever of `entity_ref`/`query_ref`/`event_ref`/`external_label` is set — never persisted.

These vocabularies collided rather than composed: Flow's `service` kind is assigned to *any* `component`-kind `entity_ref` regardless of the Component's actual `type`, so a `website`- or `worker`-typed Component renders identically to a `service`-typed one — same fixed `Cube` icon, same fixed green — literally showing the wrong type for 3 of 4 subtypes. Flow's `query`/`event` kinds mirror `ApiEndpoint`/`ApiOperation` but under different words ("Query" reads as read-only, which an Endpoint backing a POST/DELETE call is not), and their per-instance HTTP-method/direction color (`METHOD_COLORS`/`DIRECTION_COLORS`, `plugins/flows/frontend/src/lib/flowNodePalette.ts:137-165` — already a duplicate of `METHOD_THEME`/`DIRECTION_THEME` per the plugin import-boundary rule, `plugins/flows/backend/atlas_plugin_flows` spec's "No core module depends on Flow..." requirement) drives only the card border, not the chip text next to it, which still shows the static word "Query"/"Event".

Separately, `FlowStepQueryRef`/`FlowStepEventRef` (`core/frontend/src/lib/types.ts:12-25`) are documented, intentional point-in-time snapshots — "captured when the reference is chosen, never re-fetched." `atlas_plugin_apis.extension_points.resolve_endpoint`/`resolve_operation` (`plugins/apis/backend/atlas_plugin_apis/extension_points.py:77-100`) already exist and are already called cross-plugin by `atlas_plugin_flows.models._resolve_query_or_event_ref` (`plugins/flows/backend/atlas_plugin_flows/models.py:78-113`) at **save** time, to validate that a `query_ref`/`event_ref` resolves — explicitly permitting a `removed` Endpoint/Operation to still resolve (removal doesn't invalidate an existing reference, per the `api-endpoints`/`api-operations`/`flow-query-event-steps` specs). No **read**-time path exists today that surfaces that same status back to a Flow's viewer; a Flow's `steps` JSONField is returned to the frontend verbatim.

Finally, a live visual bug was found and measured during this design's review: `CARD_STYLE_BASE` (`plugins/flows/frontend/src/components/FlowNodes.tsx:33-45`) uses a fixed-height flex column with `justifyContent: 'center'`, added by the prior `flow-canvas-palette-unification` change so every card kind renders the same total height. Measured live (`localhost:5173/flows/1/edit`, step `step-8`) via DOM inspection: a 3-line card (chip+title+subtitle) has its chip start at relative-Y 6.4 (of a 45px scaled card); a 2-line card (chip+title, no subtitle) has its chip start at 11.3 — chip and title shift down by design, because centering redistributes free space on both sides of the shrunk content block, not only below it.

## Goals / Non-Goals

**Goals:**
- Flow's node-kind vocabulary stops colliding with, and stops needlessly diverging from, the vocabulary Components/APIs already use.
- A Component or API-backed Flow node shows the real subtype's icon/color, not one fixed identity for every subtype.
- An API Call/Event node's chip shows the real method/direction, using the color mapping that already exists and already matches the target scheme — no new color decisions.
- A Flow author gets a passive, read-only visual warning when a node's Endpoint/Operation reference has gone stale (removed or deprecated) since it was chosen, without the reference being silently or automatically touched.
- Every node card's chip+title sit at the same vertical position whether or not a subtitle/summary is present.
- The unrelated meanings of Flow's `external` kind and the catalog's `External` tag are made explicit in-product, without merging them.

**Non-Goals:**
- No change to the persisted Flow `steps` JSON grammar: `entity_ref`, `external_label`, `query_ref`, `event_ref` keep their exact field names and shapes. `FlowNodeKind` is a derived, in-memory value only — renaming it is not a data migration.
- No change to `ApiEndpoint`/`ApiOperation` removal semantics: a `removed` Endpoint/Operation still resolves successfully on Flow save (per `flow-query-event-steps`); this change only adds a way to *see* that status, not a way to change it.
- No renaming of backend models, fields, or routes in `atlas_plugin_apis` (e.g. `ApiEndpoint`, `operation_id`, `/apis/{apiId}/endpoints/{endpointId}`). The catalog tab-label change (decision 2) is UI copy only.
- No raw hex colors anywhere in the Flow palette. `GravityLabelTheme` (`flowNodePalette.ts:19`) stays restricted to Gravity UI's named semantic tokens so the canvas keeps automatic light/dark support via `ThemeProvider`. A custom teal hex for PATCH was explicitly considered and rejected in favor of keeping `utility` (see Decision 3).
- No linkage between a Component/System/API tagged `"External"` in the catalog and Flow's `external` node kind. `flowNodeKindOf` continues to never read `metadata.tags`; this remains a considered-and-deferred idea, not a TODO.
- No automatic node removal or mutation when a reference is found stale.

## Decisions

### 1. Rename `FlowNodeKind` values; surface real Component/API subtype identity

`service` → `component`; `query` → an internal key `call`, displayed as **"API Call"**; `event` is unchanged. This only touches computed-value lookup tables (`FLOW_NODE_KIND_LABELS`/`FLOW_NODE_KIND_ICONS`/`FLOW_NODE_PALETTE`/`ENTITY_REF_KIND_TO_NODE_KIND`/`FLOW_NODE_TYPES`) and component names (`EntityFlowNode`/`QueryNode`→`CallNode`/`EventNode`) — `flowNodeKindOf`'s derivation inputs (`entity_ref`/`query_ref`/`event_ref`/`external_label`) are untouched, so no persisted data changes shape.

Component-backed (`component`-kind) and API-backed (`api`-kind) nodes additionally resolve their real subtype (`service|website|library|worker`, `openapi|grpc|asyncapi|graphql`) and look up its icon/color from a new table in `flowNodePalette.ts`/`flowNodeKind.ts`, duplicated from `COMPONENT_TYPE_ICONS`/`COMPONENT_TYPE_THEME`/`API_TYPE_ICONS`/`API_TYPE_THEME` — the same duplication pattern `METHOD_COLORS`/`DIRECTION_COLORS` already establish for HTTP method/direction, required because `atlas_plugin_flows` cannot import `atlas_plugin_standard_catalog`/`atlas_plugin_apis` frontend modules directly. This requires the `entity_ref` resolution `EntityNodeComponent` already depends on (`FlowNodes.tsx:157-172`) to carry the resolved entity's `type` alongside its name — implementation should check whatever hook/query backs that resolution today and extend its selected fields rather than adding a second fetch.

**Alternative considered:** keep Flow's own vocabulary (Service/Query/Event) as pure "role in the flow" language, distinct on purpose from catalog nouns, and only add a subtitle/tooltip explaining the mapping. Rejected — the collision on `service` is not cosmetic (it's the same literal string as one of four `ComponentType` values, and produces a visibly wrong badge for the other three), and fixing the icon/color-by-subtype work (goal 2) required touching the same rendering code anyway, so keeping the generic label alongside correct per-subtype color would leave the fix half-done.

**Alternative considered:** rename `query` to `endpoint`. Rejected in favor of "API Call" — "Endpoint" ties the node to REST/OpenAPI specifically (the catalog now also uses "Operations" for this concept, see Decision 2), whereas "API Call" reads correctly for gRPC/GraphQL as well as REST, and reads as a *shape of interaction* (a Flow-level concern) rather than a catalog noun Flow would otherwise have to keep in sync with.

### 2. Catalog: unify the "Endpoints" tab label to "Operations"

`plugins/apis/frontend/src/entityDetailTabs/api.tsx:110`'s `label: 'Endpoints'` (shown when `entity.spec.type === 'openapi'`) becomes `label: 'Operations'`, matching the label already used at line 117 for `asyncapi`-typed APIs. The underlying `id: 'atlas.apis.api.endpoints'`, route, and `ApiEndpointsTab`/`ApiEndpoint` model/component names are unchanged — this is copy-only, so no route or deep-link breaks. `ApiDetailPage.test.tsx`'s two `{ name: 'Endpoints' }` assertions (lines 170, 176) are updated to `'Operations'`.

Rationale: OpenAPI's own spec vocabulary already calls a path+method combination an "Operation Object" with `operationId` — `ApiEndpoint` already has an `operation_id` field (`endpoint.py`), so "Endpoint" was Atlas's own added term, not the underlying spec's. After this change, "Operation" is the catalog's umbrella term for a single API interaction regardless of protocol or sync/async shape, which is *why* Decision 1 explicitly keeps Flow's async kind named "Event" rather than renaming it to "Operation": once the catalog uses "Operation" for both Endpoints and Operations, applying it to only the async Flow kind would newly be wrong, not newly right. Flow's "API Call" vs "Event" becomes its own vocabulary for interaction *shape*, no longer trying to mirror a catalog noun word-for-word.

**Alternative considered:** rename `ApiEndpoint` itself (model, fields, routes) to fully merge with `ApiOperation`'s vocabulary. Rejected as much larger blast radius (route/URL changes, `ServiceEndpointUsage` naming, importer code) for a change whose motivating pain point is UI wording, not the data model — the two remain intentionally separate Django models (method+path vs channel+direction) and mutually-exclusive tabs; only the human-facing label unifies.

### 3. API Call/Event chip shows the real method/direction

`QueryNodeComponent`/`EventNodeComponent` (renamed per Decision 1) currently pass a static `label={FLOW_NODE_KIND_LABELS.query}`/`.event` to `NodeCard` while the border color is already correctly derived per-instance (`queryMethodColors`/`eventDirectionColors`). Change the chip label to the resolved value itself — the HTTP method (`"GET"`, `"POST"`, …) for an API Call node, the direction title-cased (`"Send"`/`"Receive"`) for an Event node — falling back to the generic "API Call"/"Event" label only when the ref is unresolved, mirroring the existing `subtitle ? ... : undefined` fallback already used for the subtitle line.

No change to `METHOD_COLORS`/`DIRECTION_COLORS`. The target scheme (GET=info, POST/PUT=success/warning per existing assignment, PATCH=utility, DELETE=danger) was reviewed against the existing table and found identical — the only gap was the chip text, not the color.

**Alternative considered:** a custom hex (`#50e3c2`, teal) for PATCH, to visually distinguish it from PUT more strongly than the current shared "blue-grey-ish" `utility` token. Rejected — `GravityLabelTheme` (`flowNodePalette.ts:19`) is deliberately restricted to Gravity UI's seven named semantic tokens specifically so the palette gets light/dark support for free via `ThemeProvider`, and `<Label theme=...>` (the chip's own rendering primitive) does not accept an arbitrary hex at all; introducing one would mean bypassing `Label`'s theme system for one kind's one method, breaking the single-source-of-truth pattern the rest of the palette follows. Kept `utility`.

### 4. Stale Endpoint/Operation reference indicator

**Mechanism:** reuse `atlas_plugin_apis.extension_points.resolve_endpoint`/`resolve_operation` (`extension_points.py:77-100`) — already the sanctioned cross-plugin lookup, already called by `atlas_plugin_flows.models._resolve_query_or_event_ref` at save time — but call them again at **read** time. When a Flow is fetched, for each step carrying a `query_ref`/`event_ref`, resolve the current Endpoint/Operation by id and attach its live `status`/`deprecated` alongside the existing snapshot, without altering the stored snapshot itself. This keeps the new integration surface consistent with the one the `flow-query-event-steps`/`flows-plugin` specs already document ("no import of another plugin's implementation module... only declared `.contracts`/`.extension_points` submodules") — no new import-boundary exception is needed, since it's the same functions, same guard pattern (`django_apps.is_installed('atlas_plugin_apis')`).

**Where to compute it:** as a response-shape addition on the Flow read endpoint (e.g., a sibling map keyed by step id, alongside the existing verbatim `steps` array), computed at serialization time — not stored on the Flow row, so it's always current as of the read and requires no migration. The exact response shape (inline per-step field vs. a separate top-level map) is left to implementation; either satisfies the requirement as specced (see `flow-query-event-steps` delta) as long as it's per-step and computed at read time.

**Rendering:** when a resolved Endpoint's `status === 'removed'` or `deprecated === true`, or a resolved Operation's `status === 'removed'`, show an orange `TriangleExclamation` icon on the API Call/Event card with a tooltip explaining why — reusing the exact visual precedent already in the catalog (`EndpointDetailPage.tsx:96-98`'s `<Label theme="warning" icon={<Icon data={TriangleExclamation}/>}>Deprecated</Label>`, and the removed-`Alert` copy tone at lines 102-114 of the same file). This is a read-only signal: the step's `query_ref`/`event_ref` is never rewritten or removed as a result.

**Alternative considered:** a frontend-only batched lookup (the canvas fetches every referenced Endpoint/Operation's current status itself, on load, via the existing public list/detail Endpoints once the flow's steps are known). Rejected in favor of a server-computed field — it reuses an existing, already-vetted function pair instead of opening a new public read surface, and avoids N (or one batched-but-bespoke) extra client-side requests plus client-side cross-referencing logic that the server can do in one pass while already loading the Flow.

### 5. Card content is top-anchored, not block-centered

Change `CARD_STYLE_BASE`'s `justifyContent: 'center'` (`FlowNodes.tsx:33-45`) to top-anchor content (e.g. `justifyContent: 'flex-start'` with the existing fixed padding), so the chip and title always render at the same fixed Y-offset from the card's top edge, whether or not a subtitle/summary is present — any empty space appears only below the title, where a subtitle would have gone. The card's overall fixed height (84px, established by the prior `flow-canvas-palette-unification` change so no kind renders shorter than another) is preserved; only the distribution of free space within it changes. Applies uniformly to every kind sharing `NodeCard` (all of them), since Query/Event's subtitle is equally conditional on ref resolution.

**Alternative considered:** keep block-centering, since it was adopted deliberately in the prior `flow-canvas-palette-unification` change. Rejected after live measurement (`localhost:5173/flows/1/edit`, step `step-8`) showed centering does not, in fact, deliver "same position regardless of content" — it delivers "same total height," a different and already-separately-preserved goal; the position-consistency goal needs top-anchoring specifically.

### 6. External naming — clarify, don't merge

Add a short clarifying tooltip/help text to Flow's External tile (`FlowStepModal.tsx`) and/or the rendered External node, stating explicitly that it represents a step with no catalog record at all — distinct from the catalog's `External` tag, which marks a real cataloged entity (e.g. a Component or System representing a third-party vendor like Stripe) as third-party. No code path linking a tagged-External catalog entity to Flow's `external` kind is added.

**Alternative considered (deferred, not rejected outright):** teach `flowNodeKindOf` to also treat an `entity_ref`'d Component/System/API tagged `"External"` in the catalog as Flow's `external` kind (or at least apply its color), unifying the two meanings for real. Deferred — this is new integration scope (reading `metadata.tags` during kind derivation, deciding whether a tagged entity should still show as `component`/`api` styled or switch to `external` styled) that the user did not ask for in this round; captured here so a future change can pick it up deliberately rather than rediscovering the question.

## Risks / Trade-offs

- **[Risk]** Renaming `FlowNodeKind` values touches every file listed in the proposal's Impact section across two components (`EntityFlowNode`, `QueryNode`→renamed) — a partial rename (e.g. missing one lookup table) would silently fall through to `undefined` icon/color. → **Mitigation:** rely on TypeScript's exhaustiveness — every `Record<FlowNodeKind, ...>` table (`FLOW_NODE_KIND_LABELS`, `FLOW_NODE_KIND_ICONS`, etc.) is keyed by the `FlowNodeKind` union itself, so renaming the union member and re-running the type-checker surfaces every table that still needs updating as a compile error, not a runtime gap.
- **[Risk]** The new read-time `resolve_endpoint`/`resolve_operation` calls run once per API Call/Event step on every Flow read, which is an N+1-shaped query pattern for a Flow with many such steps. → **Mitigation:** batch by collecting all referenced ids per Flow and issuing one `filter(pk__in=...)` per kind (mirroring `resolve_api_spec_url`'s existing `select_related`/batched style in the same plugin) rather than calling the single-id resolver in a per-step loop; call this out explicitly in tasks.md so it isn't implemented as a naive loop.
- **[Risk]** Test churn: assertions matching the literal strings "Service"/"Query"/"Event"/"Endpoints" (component tests, `ApiDetailPage.test.tsx`, any Flow canvas snapshot/DOM tests) will fail until updated. → **Mitigation:** tasks.md includes an explicit test-sweep task; this is expected, mechanical churn, not a design risk to the approach itself.

## Migration Plan

No database migration is required for any part of this change:
- Decision 1's rename is a computed-value/lookup-table rename; `FlowNodeKind` is never persisted.
- Decision 2's tab-label change is UI copy; no model/field/route change.
- Decision 4's stale-status surfacing is computed at read time from existing `ApiEndpoint`/`ApiOperation` rows; nothing new is stored on `Flow`.
- Decisions 3, 5, and 6 are rendering/copy-only changes with no data-shape implications.

Rollback for any part is a plain revert of the affected frontend/backend files — no forward-only data changes are introduced.

## Open Questions

- Exact response shape for Decision 4 (inline per-step field on the existing Flow serializer vs. a separate top-level map keyed by step id) — left to implementation; the `flow-query-event-steps` delta spec below is written to be satisfied by either.
- Whether "API Call" is the final preferred label vs. an even shorter alternative (e.g. just "Call") — captured as "API Call" per the discussion this change consolidates; open to bikeshedding at implementation review, but not blocking.
