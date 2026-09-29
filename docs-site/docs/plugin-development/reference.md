---
title: Plugin API reference
description: Exact public Python and TypeScript extension contracts.
audience: [plugin-author]
page-type: reference
---

# Plugin API reference

Atlas ships two contract packages for plugins: `atlas_plugin_api` (Python, backend) and
`@atlas/plugin-api` (TypeScript, frontend). Both are internal 0.x contracts. Every
first-party plugin uses them, and they are versioned, but they are not yet a published,
externally stable SDK.

This is a lookup page. Start from the guide that motivates a contract, then
return here for its exact exported shape:

| Need | Guide | Contract |
| --- | --- | --- |
| Describe and select a plugin | [Plugin layouts](plugin-layouts.md) | `PluginDescriptor` |
| Own catalog data | [Entity kinds and facets](entity-kinds-and-facets.md) | `EntityKindHandler`, `register_kind` |
| Call or publish backend behavior | [Backend collaboration](backend-collaboration.md) | capability and extension registries |
| Protect an action | [Plugin permissions](permissions.md) | `register_permission`, `PolicyEvaluator` |
| Read typed configuration | [Plugin configuration](plugin-configuration.md) | `PluginConfigSchema`, `SecretRef` |
| Implement browser authentication | [Authentication provider SDK](authentication-provider-sdk.md) | `atlas.auth.providers.v1` contracts |
| Contribute user interface | [Frontend contributions](extension-points.md) | contribution builders |
| Plan data and background work | [Models, migrations, and jobs](models-migrations-and-jobs.md) | `django_apps`, `job_ids` |

## Python: `atlas_plugin_api`

### Declaring a plugin

```python
@dataclass(frozen=True)
class PluginDescriptor:
    id: str
    version: str
    compatibility: Mapping[str, str]
    django_apps: tuple[str, ...]
    entry_point: str
    requires_plugins: Mapping[str, str] = {}
    config_schema: type[PluginConfigSchema] | None = None
    job_ids: tuple[str, ...] = ()
    authentication_providers: tuple[AuthenticationProviderContribution, ...] = ()
```

`entry_point` is a `module:attribute` reference pointing back at this same descriptor (matching
the `atlas.plugins` entry-point convention), e.g. `"atlas_plugin_yourplugin.plugin:PLUGIN"`.
`compatibility` describes the Core range the plugin supports; `requires_plugins`
declares selected plugin dependencies; `django_apps` owns models and migrations;
`job_ids` declares scheduler ids paused when the plugin is disabled. See
[compatibility and lifecycle](compatibility-and-lifecycle.md).

### Authentication providers (`atlas.auth.providers.v1`)

Authentication providers use a keyed, versioned extension contract. Static
metadata is carried by `PluginDescriptor.authentication_providers` and remains
safe to import before `django.setup()`. Runtime code registers exactly one
implementation per provider id after setup:

```python
from atlas_plugin_api import (
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    PluginDescriptor,
    register_authentication_provider,
)

PROVIDER = AuthenticationProviderDescriptor(
    id="example.auth.directory",
    flow_kind=AuthenticationFlowKind.REDIRECT,
    presentation=AuthenticationProviderPresentation(display_name="Directory SSO"),
)

PLUGIN = PluginDescriptor(
    # ordinary descriptor fields omitted
    authentication_providers=(AuthenticationProviderContribution(descriptor=PROVIDER),),
)


def register_runtime() -> None:
    register_authentication_provider(DirectoryProvider(), owner=PLUGIN.id)
```

Use `CredentialAuthenticationProvider` for a single-step credential verifier
and `RedirectAuthenticationProvider` for start/callback protocols. Their
contexts contain only provider/source identity, Core attempt/correlation ids,
an operation deadline, and flow-specific callback data. They expose no Core
registry, ORM model, session helper, or Django request.

A successful provider returns `VerifiedIdentity`: a non-empty stable subject
scoped by provider and immutable source, normalized `ExternalProfile`,
provenance-bearing `AssuredAttribute` values, and an explicit
`ExternalGroupSnapshot` (`complete`, `unavailable`, or `unsupported`). A
complete snapshot may intentionally be empty. Call `validate_for(...)` before
provisioning to reject provider/source mismatch. Failures cross the boundary
only as `AuthenticationFailure` with an allowlisted category and retryability;
credentials and callback parameters have redacted representations.

`get_authentication_provider_lookup()` is Core's read-only registry view. It
can resolve or enumerate registered providers but cannot mutate the registry.
Duplicate registration raises `DuplicateAuthenticationProviderError` and
identifies both owners. Provider plugins register through
`register_authentication_provider()` and must not import Core authentication,
settings, model, or session modules, nor undocumented `allauth.*.internal`
modules. Use the [provider SDK tutorial](authentication-provider-sdk.md) for
flow selection, packaging, contract tests, failure handling, and the LDAP
search-and-bind mapping.

### Entity kinds

```python
@runtime_checkable
class EntityKindHandler(Protocol):
    kind_id: str
    spec_schema: type[BaseModel]
    provides: list[str]

    def create_details(self, entity: CatalogEntity, spec: BaseModel) -> None: ...
    def update_details(self, entity: CatalogEntity, spec: BaseModel) -> None: ...
    def serialize_details(self, entity: CatalogEntity) -> BaseModel: ...
    def validate_delete(self, entity: CatalogEntity) -> None: ...


def register_kind(handler: EntityKindHandler, *, owner: str | None = None) -> None: ...
```

`ValidateDeleteError`, raised from `validate_delete`, vetoes a delete inside the same transaction
the Entity Service runs it in. `DuplicateKindError` is raised if a second handler tries to
register an already-claimed `kind_id`. See
[Entity kinds & facets](entity-kinds-and-facets.md) for how these fit together.

### Capabilities

```python
def resolve_capability(capability_id: str) -> CapabilityResult[object]: ...
```

`CapabilityResult` is `Ok(value) | Unavailable() | Error(reason)`. A consumer gets a typed
result instead of `object | None`, so "nothing provides this capability" cannot be mistaken for
a successful call that happens to return something falsy.

### Permissions and authorization

```python
def register_permission(permission_id: str, *, owner: str | None = None) -> None: ...


class PolicyEvaluator(Protocol):
    def check(
        self, principal: Any, permission: str, resource: CatalogEntity | None
    ) -> bool: ...


def get_policy_evaluator() -> PolicyEvaluator: ...
```

A plugin declares its own permission ids and asks the distribution's Policy Evaluator for a
decision. The plugin does not implement authorization logic itself.
The declaration belongs in `register_runtime()` and the check belongs at the
backend resource boundary; see [Plugin permissions](permissions.md).

### Plugin configuration

```python
class SecretRef(BaseModel):
    from_env: str  # manifest's {fromEnv: VAR}


class PluginConfigSchema(BaseModel):
    PUBLIC_FIELDS: ClassVar[frozenset[str]] = frozenset()
```

Subclass `PluginConfigSchema` for your plugin's own configuration; type any field that might hold
a secret as `<type> | SecretRef`. Only `resolve_secrets` (called once by core, at startup) ever
reads the referenced environment variable. The manifest, lock file, and frontend bundle see only
the `SecretRef` itself. List a field in `PUBLIC_FIELDS` only if it is genuinely safe
to send to the frontend; nothing is exposed by default. See [Plugin
configuration](plugin-configuration.md) for the complete declaration,
manifest, runtime-resolution, frontend-consumption, and test workflow.

### Working with entities

`CatalogEntity`, `get_catalog_entity_model()`, `parse_ref`/`resolve_ref` (for `kind/name`-style
references), `entity_relations`/`recompute_relations`, and the `KIND_*` constants for the kinds
Standard Catalog and the APIs plugin register are all exported from the top-level package, so a
plugin never needs to reach into `server.apps.catalog` directly to work with catalog data.

`MetadataIn` and `MetadataPatch`, the shared metadata envelope for entity create and patch
requests, bound their fields: `title` 255 characters, `description` 4,096, `documentation`
1 MiB, `labels` and `tags` 100 entries each, `links` 50 entries (each link `url` 2,048
characters, `title` 255, `type` 64). A request that exceeds a limit is rejected with a
field-attributed validation error. Plugin request schemas that accept free text or lists should
bound them the same way; the APIs and Database Schema plugins cap inline `spec_content` and
`source_sql` at 2 MiB, and Flows caps `steps` at 500 entries.

### Outbound HTTP

```python
from atlas_plugin_api import BlockedAddressError, safe_request

response = safe_request(
    "https://specs.example.com/openapi.yaml",
    timeout=10,
    max_redirects=5,
    max_response_bytes=10 * 1024 * 1024,
)
response.status_code, response.headers, response.content
```

Use `safe_request` instead of calling `requests` directly whenever a plugin fetches a URL or
host that an operator or user supplied. It rejects URLs with embedded credentials or a fragment
and, unless the call passes `allow_http=True`, any scheme other than `https`. It resolves the
hostname once, refuses the request when the host resolves only to private, loopback,
link-local, multicast, or otherwise reserved addresses, and connects to that verified address so
a second DNS answer cannot redirect the connection. Every redirect is validated the same way, and
`max_redirects=0` disables redirects. The body is read incrementally and aborted at
`max_response_bytes` (default 10 MiB). `exempt_hosts` lets a caller with its own operator
allowlist exempt exact hostnames from the address check; the exemption is evaluated per hop and
does not carry over a redirect to another host.

Failures raise `SafeHttpError` subclasses: `UnsafeUrlError`, `BlockedAddressError`,
`TooManyRedirectsError`, and `ResponseTooLargeError`. Catch `SafeHttpError` to treat any rejected
fetch uniformly. The APIs plugin's `spec_url` fetch uses this helper. The OIDC and Gitea
providers apply the same resolve-once, connect-to-the-verified-address rule to their
token-exchange and userinfo calls through the helper's shared pinned-connection adapter.

## TypeScript: `@atlas/plugin-api`

### Authentication presentation

`AuthenticationProviderPresentation`, `AuthenticationProviderBootstrap`, and
`AuthenticationBootstrapConfig` mirror the safe public projection of
`atlas.auth.providers.v1`. They contain provider id, contract/flow kind,
display and credential-field metadata, default/signup behavior, remote-logout
capability, and the provider-choice URL only. Connection endpoints, issuers,
client credentials, mappings, raw claims, and resolved secrets have no field in
these types.

### Declaring a plugin

```typescript
function defineFrontendPlugin(plugin: { id: string; contributions: readonly Contribution[] }): FrontendPlugin
```

### Contribution builders

```typescript
function route(input: Omit<RouteContribution, 'type'>): RouteContribution
function navItem(input: Omit<NavItemContribution, 'type'>): NavItemContribution
function entityDetailTab<TEntity>(input: Omit<EntityDetailTabContribution<TEntity>, 'type'>): EntityDetailTabContribution<TEntity>
function homeWidget(input: Omit<HomeWidgetContribution, 'type'>): HomeWidgetContribution
function routeRef(id: string): RouteRef
function entitySupports(capability: string): (entity: { capabilities?: readonly string[] }) => boolean
```

Every builder is a pure function that returns an immutable data object without a side effect.
`routeRef` gives you a lazy reference to a route id. The frontend resolves it when it composes
every plugin's contributions, which lets a `navItem` point to a route that is not yet defined in
file-load order.

### Contribution types

```typescript
type ExtensionPointCardinality = 'collection' | 'singleton' | 'keyed'

type Contribution =
  | RouteContribution
  | NavItemContribution
  | EntityDetailTabContribution<any>
  | HomeWidgetContribution
```

`RouteContribution.public` defaults to `false`; set it `true` to bypass the session guard and nav
shell layout core wraps every other route in (used for something like a login page).
`EntityDetailTabContribution.fullWidth` lets canvas-like tab content (a diagram, an editor) use
the shell's full width instead of its default right-rail layout.

### Composition

```typescript
function composeFrontendPlugins(plugins: readonly FrontendPlugin[]): ComposedContributions
```

Runs at frontend build time against every selected plugin's declared contributions. A duplicate
contribution id or a route path colliding with a core-reserved path (`CORE_RESERVED_PATHS`) fails
the build and raises `CompositionError`.

### Runtime configuration

```typescript
interface BootstrapConfig {
  // ...
}
type PluginPublicConfig
type PublicConfigValue
```

The frontend reads each installed plugin's public configuration projection through these types.
`PluginConfigSchema.public_projection()` produces the same `PUBLIC_FIELDS`-gated projection on
the backend, with no secret values. The [Plugin configuration](plugin-configuration.md#expose-a-public-frontend-projection)
guide explains how to consume the keyed projection safely.

### Data lifecycle and scheduled jobs

The descriptor's `django_apps` is the ownership boundary for a plugin's models,
migrations, and explicit purge scope. `job_ids` tells runtime startup which
`django-apscheduler` jobs to pause or resume with plugin lifecycle. Read
[Models, migrations, and jobs](models-migrations-and-jobs.md) before adding either.
