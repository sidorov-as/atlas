## Context

All first-party plugins that expose entity metadata reuse the shared `MetadataIn`/`MetadataPatch`/`LinkSchema` Pydantic models from `plugin-api/python/atlas_plugin_api/schemas.py` (`CamelModel` base, Pydantic v2). None of `title`, `description`, `documentation`, `labels`, `tags`, or `links` carry a `max_length`/count constraint today — only `name` has a validator, and that validator only checks emptiness and forbidden characters, not length. The same unbounded-string pattern repeats in plugin-specific "large inline content" fields: `ApiSpecIn.spec_content` (inline OpenAPI/AsyncAPI/GraphQL/gRPC spec text), `DatabaseSchemaIn.source_sql` (inline SQL DDL), and `FlowIn.steps` (a `list[dict]`, plus its own `description`/`documentation` strings that don't go through `MetadataIn`).

## Goals / Non-Goals

**Goals:**
- Every field that currently accepts unbounded attacker-controlled content gets an explicit, enforced bound at the Pydantic validation layer.
- Limits are generous enough not to reject realistic legitimate content (long Markdown docs, sizeable inline OpenAPI specs, SQL DDL for a real schema).
- The fix is scoped to validation (reject at the API boundary), not database migrations — this is a DoS-prevention change, not a data-modeling change.

**Non-Goals:**
- Bounding content fetched via `specUrl` — that's `fix-apis-ssrf`'s streaming/byte-cap responsibility; this change only bounds *inline*-provided content.
- Retroactively truncating or migrating existing stored rows that already exceed the new limits.
- Enforcing limits at the database column level (e.g. `TextField(max_length=...)` with a matching DB constraint) — Pydantic-layer validation is the fix; a follow-up could add DB-level enforcement defense-in-depth, but it's not required here.
- Touching `c4` or `standard-catalog` plugin schemas — reviewed and found no additional unbounded free-text/list fields beyond what's already covered via the shared `MetadataIn`/relationship schemas.

## Decisions

- **Fix at the shared `MetadataIn`/`MetadataPatch`/`LinkSchema` level, not per-plugin.** Every plugin using entity metadata (System, Component, Resource, API, and anything built on the standard-catalog kinds) inherits the fix automatically, instead of needing the same limits re-added in each plugin's own schema.
- **Extend beyond the audit's two cited files to `source_sql` and `flows.steps`/`description`/`documentation`.** These were found during this change's own investigation to have the identical unbounded-attacker-controlled-content shape as the audit's examples. Fixing them now avoids a second audit finding later and keeps the "large inline content" fix consistent across plugins instead of piecemeal.
- **Limits chosen generously, not tightly.** The goal is DoS prevention (bound the worst case), not UX-driven content limits — e.g. `documentation` as Markdown documentation for a real system can legitimately be tens of KB; the limit should be well above realistic legitimate use and only stop pathological/attacker-sized input (e.g. hundreds of KB to MB range per field, exact values to be set during implementation after checking current data).
- **Enforcement at the Pydantic schema layer only.** This is the point every write already passes through (`CamelModel` request/patch schemas), so it's the cheapest, most centralized place to reject oversized input — no need to duplicate the check in views, serializers, or the database layer for this change's threat model (storage/parsing DoS from oversized single requests, not slow accumulation via many small writes).

## Risks / Trade-offs

- **Breaking existing content that exceeds new limits** → mitigate by checking real data (via a read-only query/audit before implementation) for the longest current values in each affected field, and setting limits comfortably above the observed maximum plus headroom for growth.
- **Limits chosen too tight, breaking legitimate future use (e.g. a large but valid inline OpenAPI spec)** → mitigate by erring generous (order of magnitude above typical legitimate size) rather than minimal; a future change can tighten based on real usage data if needed.
- **Inconsistent enforcement if a future plugin adds its own free-text field without reusing `MetadataIn`** → out of scope for this change to prevent structurally (no shared "all plugin schemas must bound their strings" lint exists), but worth noting as a residual gap; not blocking this change.

## Migration Plan

1. Query production-representative data (or the closest available data) for current max lengths of each affected field, to sanity-check chosen limits before implementation.
2. Add `max_length`/count constraints to `plugin-api/python/atlas_plugin_api/schemas.py` (`MetadataIn`, `MetadataPatch`, `LinkSchema`).
3. Add the equivalent constraint to `ApiSpecIn.spec_content`/`ApiSpecPatch.spec_content`.
4. Add the equivalent constraint to `DatabaseSchemaIn.source_sql`/`DatabaseSchemaPatch.source_sql`.
5. Add the equivalent constraints to `FlowIn.description`/`documentation`/`steps` and `FlowPatch` counterparts.
6. Add negative tests per field (create/patch with content over the limit → rejected with a clear error).
7. No rollback complexity beyond reverting the validators — no data migration is performed.

## Open Questions

- Exact numeric limits per field are left to implementation time, informed by step 1's data check, rather than fixed here — this design specifies the *mechanism and scope*, not final numbers.
