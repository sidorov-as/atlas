## Context

Atlas is currently docs-only: `docs/design.md`, three ADRs, and `CONTEXT.md` describe the intended v1 slice, but no Django project, React project, database schema, or Docker Compose stack exists. This change builds that first implementation. `entity-claim-arbitration` (already proposed) depends on it landing first — its tasks assume entity models, an ingestion upsert, and an owner-Group permission check that this change creates.

## Goals / Non-Goals

**Goals:**
- A running Docker Compose stack (`postgres`, `backend`, `frontend`, `ingestor`) implementing every "In scope" item in design.md §2 except the arbitration/namespace work carved out to `entity-claim-arbitration`.
- Entity storage and CRUD for all six kinds, with real FK/M2M relationships for `spec` reference fields (not free-text refs), so relation derivation is a query, not string parsing.
- A minimal YAML-managed/manual provenance marker sufficient for the original ADR 0001 rule (read-only if ingested, editable by owner-Group members if manual) — deliberately simple, since `entity-claim-arbitration` extends it.

**Non-Goals:**
- `source_kind` enum, repository FK for arbitration purposes, conflict recording, adoption, namespace column, case-insensitive uniqueness, ref parsing with namespace support — all `entity-claim-arbitration`.
- Real C4 diagram rendering (stays a stub per ADR 0002), SSO providers (ADR 0003), object storage (ADR 0002), any `Domain`/`Location`/`Template` kind, Service Health/Activity (design.md §2).

## Decisions

**Concrete Django model per kind, sharing an abstract envelope base.** System, Component, Resource, API, Group, User each get their own model (inheriting `name`, `title`, `description`, `labels`, `tags`, `links` from an abstract base), rather than one generic `Entity` table with a JSON `spec` column. A JSON-spec approach was considered and rejected: `spec` reference fields (`owner`, `system`, `dependsOn[]`, `providesApis[]`, ...) are exactly what relation derivation reads, and modeling them as real FK/M2M relationships makes that derivation a query instead of parsing ref strings out of JSON on every read.

**Ref strings are a computed representation, not the storage format.** Since spec reference fields are real FKs, an entity's `kind:name` ref is derived (a serializer field / model property), and ingestion resolves an incoming ref string to a row via one shared resolver function. This keeps a single place where ref parsing happens, which matters because `entity-claim-arbitration`'s namespace-aware parser (ADR 0004) replaces that one function rather than touching every call site.

**Provenance: a single nullable FK, not an enum.** Each ingestible entity gets `ingested_from: FK[RegisteredRepository, null=True]`. Manual = null; YAML-managed = set. This is the minimal thing that satisfies the original ADR 0001 rule (read-only in UI/API when set, editable by owner-Group members when null) and the §9 read-only banner (renders `ingested_from.full_name`). `entity-claim-arbitration` is expected to extend this into an explicit `source_kind` enum alongside it, not replace it outright — a straightforward additive migration, not a rewrite.

**Relations: one generic table, not per-predicate join tables or `GenericForeignKey`.** `Relation(subject_kind, subject_id, predicate, object_kind, object_id)`, with `subject_kind`/`object_kind` constrained to the six known kinds. `django.contrib.contenttypes.GenericForeignKey` was considered and rejected as unneeded indirection for a small, fixed set of kinds; a plain `(kind, id)` pair is fully indexable and simpler to reason about. A write to any entity deletes and reinserts only that entity's outgoing `Relation` rows (design.md §3) — never a full-table rebuild.

**Ingestion transaction boundary is per-manifest, not per-run.** Each YAML document in a run is upserted in its own transaction, so one invalid document is skipped and logged (design.md §5) without rolling back the others processed in the same run.

**Diagram stub validates real entities, fakes the content.** `GET /api/diagrams/{kind}/{id}/?view=` looks up the entity by `(kind, id)` and validates `view` against the three allowed values — a real 404/400 for an invalid target — but returns one constant placeholder SVG regardless of which valid target was requested (ADR 0002).

**One DRF permission class for ownership.** A single permission class enforces: safe methods require an authenticated session; write methods additionally require `ingested_from is None` and the requesting user being a member of the entity's `owner` Group (or superuser) — the one rule in design.md §7, not split across per-viewset logic.

**Group/User membership is one `ManyToManyField`, not two independently-declared fields.** `Group.spec.members[]` and `User.spec.memberOf[]` are both serialized views over a single M2M relationship (e.g. `Group.members = ManyToManyField(User)`), not two separately-editable columns that could disagree. This was chosen over independent fields (Backstage's own shape, where the two sides can be populated by different feeds) specifically because Group and User are admin-managed only in Atlas — never ingested from two independent `catalog-info.yaml` files the way System/Component/Resource/API are — so there is no scenario where the two sides are meant to diverge, and the dual-declaration-disagreement question that would otherwise apply (design.md §12) doesn't arise: the relation table's `memberOf`/`hasMember` rows are derived by reading this one M2M from either direction, not reconciled from two sources.

**Groups/Users are seeded outside the API.** Since `/api/groups/` and (if added later) any user listing are read-only in v1, initial Groups and Users must exist before anyone can log in or own anything — seeded via Django admin and a management command for fixtures, not created through request flow.

## Risks / Trade-offs

- [Risk] Modeling spec references as real FKs instead of string refs could make the future namespace-aware ref parser (`entity-claim-arbitration`) harder to slot in → Mitigation: all ref resolution funnels through one shared function from the start, so that parser replaces one function, not scattered call sites.
- [Risk] The ingestor poll loop has no distributed lock; a run that outlasts the poll interval could overlap with the next → Mitigation: acceptable at "a few hundred entities, tens of teams" (design.md §10); an in-process guard against overlapping runs is enough, no distributed locking needed.
- [Trade-off] A generic `(kind, id)`-keyed relations table has no DB-level FK constraint guaranteeing the object side is a real row (unlike per-predicate join tables) → accepted for schema simplicity across six kinds; application-level integrity is enforced by only ever writing rows derived from validated spec fields.

## Migration Plan

Not applicable — first implementation, no existing data or running system to migrate.

## Open Questions

- Exact DRF serializer shape for spec reference fields (nested ref objects vs. bare `kind:name` strings in request/response bodies) — implementation detail, decide while building.
- Ingestor poll interval: env-configurable or hardcoded for v1 — minor, decide during implementation.
