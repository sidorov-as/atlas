## Context

`metadata.name` (Systems/Components/Resources/APIs/Group/Actor) and Flow's own `name` currently accept any string, including `""`, whitespace-only, or a string containing `/`/`:`. Three independent write paths reach `CatalogEntity`/`Flow` and all skip validation today:

- CRUD API request bodies, parsed by `MetadataIn`/`MetadataPatch` (`plugin-api/python/atlas_plugin_api/schemas.py`) and `FlowIn`/`FlowPatch` (`plugins/flows/backend/atlas_plugin_flows/api/schemas.py`).
- `catalog-info.yaml` ingestion, which validates each manifest document against the exact same `*In` schemas (`plugins/ingestion/backend/atlas_plugin_ingestion/validation.py` — its own docstring calls this "the single source of truth for both").
- Django admin, which also constructs `MetadataIn`/`MetadataPatch` (`plugins/standard-catalog/backend/atlas_plugin_standard_catalog/admin.py`).

`EntityService._apply_metadata`/`_apply_metadata_patch` (`core/backend/server/apps/catalog/services/entity_service.py`) assign validated Pydantic fields straight onto the Django model and call `entity.save()` — never `full_clean()` — so the model layer (`CatalogEntity.name = models.CharField(max_length=255)`, no `blank=False` enforcement path) provides no backstop. This means the request-schema layer is the only place a constraint can land without also changing the write pipeline itself, which is out of scope here.

## Goals / Non-Goals

**Goals:**
- Reject `name` that is empty, whitespace-only, or contains `/` or `:`, on every write path that currently reaches `MetadataIn`/`MetadataPatch` or `FlowIn`/`FlowPatch` (CRUD API, ingestion, Django admin) — for free, by fixing the schema layer once per envelope.
- Preserve existing PATCH semantics: an omitted/`None` `name` in a patch still means "leave unchanged"; only an explicitly-provided invalid string is rejected.
- Give the two entity-creation UI paths (`EntityFormShell`, `FlowFormPage`) a client-side `required` guard so the common case (user leaves Name blank) never round-trips to the server.

**Non-Goals:**
- No general kebab-case/slug naming-convention enforcement — only the two structurally-necessary characters (`/`, `:`) plus non-blank.
- No Django-model-layer change (`CatalogEntity.name` stays a plain `CharField`) and no `full_clean()` introduced into `EntityService` — the schema layer is sufficient since it's the only entry point in practice.
- No backfill/migration for any pre-existing empty-name row in a dev database.
- No change to Endpoint/Operation `name` fields (read-only, no self-service form) or to Group/Actor's admin-only forms beyond the free ride from `MetadataIn`.

## Decisions

**1. One shared validator function, exported from `atlas_plugin_api`, reused by Flow — not two separate implementations.**
`plugin-api/python/atlas_plugin_api/schemas.py` already exports factory-style validators (`ref_validator`, `optional_ref_validator`, `ref_list_validator`) that plugins import directly (`plugins/flows/backend/atlas_plugin_flows/api/schemas.py` already does `from atlas_plugin_api import ref_validator`). Adding `name_validator()`/`optional_name_validator()` next to those, exported the same way, keeps the character-checking logic in one place instead of duplicating a regex/strip routine in the flows plugin. Alternative considered: define the check inline in each schema file — rejected, since it's the same rule enforced twice with no shared source of truth, exactly the kind of drift this change is trying to remove.

**2. Validation shape: `field_validator` that strips, then checks, rather than a `Field(pattern=...)`.**
```python
_NAME_FORBIDDEN_CHARS = ("/", ":")

def _validate_name(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("name must not be empty")
    if any(char in stripped for char in _NAME_FORBIDDEN_CHARS):
        raise ValueError("name must not contain '/' or ':'")
    return stripped
```
A single `field_validator` (mirroring `_relationship_target_validator`'s existing style in the same file) reads clearer than a regex `Field(pattern=...)` for a "strip, then check, then normalize" rule, and returning `stripped` means the persisted name never carries leading/trailing whitespace even if the caller didn't trim it. Alternative considered: `Field(min_length=1)` alone (matching `ArchitectureRelationshipDeclarationIn.label`'s existing precedent) — rejected on its own because it doesn't catch whitespace-only strings or strip the value; it's not needed once the `field_validator` above exists, since the validator's own empty-check subsumes it.

**3. `MetadataPatch`/`FlowPatch` use `optional_name_validator` (skips `None`, validates any provided string) — not a required field.**
Mirrors the existing `optional_ref_validator` pattern used by `MetadataPatch`'s `owner`-style fields elsewhere in the codebase. `model_fields_set` (already used by `_apply_metadata_patch`) continues to distinguish "field omitted" from "field explicitly set", so this needs no change to `EntityService`.

**4. Remove the now-redundant manual `/`-check in `plugins/ingestion/backend/atlas_plugin_ingestion/validation.py` rather than keep it as a defense-in-depth duplicate.**
Once `MetadataIn`'s own validator rejects `/`, the hand-rolled `if '/' in document.metadata.name: raise ManifestError(...)` in `validate_manifest_document` never triggers (the `ValidationError` from `schema.model_validate(raw)` fires first and is already caught/wrapped into `ManifestError` a few lines above it). Keeping unreachable dead code around invites drift if the character set ever changes in one place and not the other. Alternative considered: leave it as belt-and-suspenders — rejected as dead code with no defense-in-depth value once the schema is the earlier, authoritative check in the same function.

**5. Frontend: `required` attribute only, no new client-side validation function.**
`EntityFormShell`'s and `FlowFormPage`'s Name `TextInput` both render inside a native `<form onSubmit=...>` (`EntityFormShell.tsx:54`, and `FlowFormPage.tsx`'s equivalent); marking the input `required` lets the browser block `handleSubmit`'s `preventDefault()` path from running at all when empty, with zero new state or logic. A submitted `/`/`:` name still reaches the server and comes back as a rejected `ValidationError`, surfaced through each form's existing `catch (err) { setError(...) }` → `<Alert theme="danger">` path — already-wired plumbing, no new UI. Alternative considered: a dedicated client-side format check (mirroring the server's forbidden-character rule) with an inline field error — rejected as unnecessary duplication of a rule that's cheap to validate server-side and rare to hit in practice (typing `/` or `:` into a name field is a deliberate edge case, not the common "forgot to fill in Name" mistake `required` already covers).

## Risks / Trade-offs

- **[Risk]** An existing `catalog-info.yaml` in some repository already has a manifest with an empty, whitespace, or `/`/`:`-containing `metadata.name` that previously ingested successfully → its next ingestion run will now fail validation for that document. **Mitigation:** this is the intended behavior (the point of the change), and ingestion already treats a single bad document as a per-document `ManifestError`, not a whole-run failure — surfaced via the existing ingestion-run-status/troubleshooting flow, no new failure mode introduced.
- **[Risk]** Any already-existing `CatalogEntity`/`Flow` row with an empty/invalid name (e.g. from manual DB manipulation or a pre-fix test) is untouched by this change and could still misbehave (e.g. fail bare-ref resolution) → **Mitigation:** explicitly out of scope (no backfill); flagged here so it isn't mistaken for an oversight.
- **[Trade-off]** Rejecting `:` is slightly broader than the currently-documented constraint (`docs-site/docs/concepts/catalog-info-yaml.md` only mentions `/`) → the docs page's "Validation constraints" paragraph needs a one-line update alongside the code change so the two don't drift apart.

## Migration Plan

No data migration. Deploy is a normal code rollout: schema validators tighten immediately on deploy, and the docs line updates in the same change. No feature flag — this is a straightforward bug fix with no compatibility concern for existing valid data (only literally-invalid names, which by definition shouldn't exist in a correctly-functioning system, start being rejected).

## Open Questions

None outstanding — all four scope decisions (strip+reject-empty, patch semantics, frontend `required`-only, forbidden `/`+`:`) were confirmed before this design was written.
