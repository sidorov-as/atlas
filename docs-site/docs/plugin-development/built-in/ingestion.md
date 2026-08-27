# Ingestion

Optional; requires Standard Catalog because it must be able to submit an Entity Intent for any
registered kind. It is backend-only and contributes no frontend package.

## What it does

Discovers `catalog-info.yaml` manifests across registered source repositories on a schedule,
parses them, and submits the result as Entity Intents for validation and reconciliation through
the Entity Service. It owns source registration, scheduling, provenance, run history, retries,
and reconciliation. Operators add source repositories rather than individual entities.

## Extension points it publishes

Unlike a core-owned registry, `atlas.ingestion.connectors.v1` and `atlas.ingestion.parsers.v1` are
owned and resolved by this plugin itself. Both are `keyed` extension points, so a second connector
(a GitLab or Bitbucket host, say) or a second manifest format registers alongside the existing
one without either needing to know about the other:

```python
class SourceConnector(ABC):
    @abstractmethod
    def list_manifest_paths(self, repo: RegisteredRepository) -> list[str]: ...
    @abstractmethod
    def fetch_file(self, repo: RegisteredRepository, path: str, ref: str) -> bytes: ...
    @abstractmethod
    def get_head_sha(self, repo: RegisteredRepository) -> str: ...
```

The only implementation registered today is `GitConnector` — provider-agnostic, registered once
per configured `atlas.ingestion` source rather than hardcoded to one host — alongside a YAML
parser for the `catalog-info.yaml` manifest format itself. The ingestion pipeline talks only to
these interfaces, resolved by key from the registries above, never directly from a git host's API
or a specific parser. Adding another connector or format does not change discovery, parsing, or
upsert.

A third, `atlas.ingestion.facet_writers.v1`, is the same shape but consumed in the opposite
direction: an optional facet plugin registers *into* it, rather than Ingestion registering into a
registry it owns for its own use. The Database Schema plugin's `register_runtime()` registers its
own `apply`/`clear` implementation under key `'database-schema'`, so a Resource manifest's declared
`spec.databaseSchema` reaches that plugin's Facet without Ingestion's core upsert path importing it
or knowing facets exist in general. Resolving a key with nothing registered — the facet plugin isn't
selected for the distribution — is a deliberate no-op, not an error; see the [Database Schema
architectural case study](database-schema.md) for the other side of this contract.

## Scheduled jobs

Runs on `django-apscheduler`, which rides along as this plugin's own dependency rather than a
core-level addition, since Ingestion is the only plugin scheduling background jobs today. Its two
jobs discover new/changed manifests across registered repositories, and periodically re-check
which registered sources have moved.

## Cross-plugin surface

Calls the APIs plugin's `due_for_spec_refresh()` on its own schedule to keep URL-sourced API
specs current. This is a direct function call because its background job pulls data on its own
timeline rather than reacting to something the APIs plugin publishes.
