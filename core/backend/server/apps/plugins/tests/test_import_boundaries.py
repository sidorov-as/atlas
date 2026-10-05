"""Python import-boundary check.

`docs/plugin-architecture.md`'s target rule is: a plugin package may import
`atlas_plugin_api` and explicitly declared contract-only packages; it may
not import core internals or another plugin's implementation. Enforced here
as a static source scan (an AST-import check, not an installed-environment
one) so it runs without a Django/plugin virtualenv.

Two allowlists document where the target rule is stricter than what the
first-party plugins actually do:

- `ALLOWED_CORE_SUBMODULES`: empty — every piece of Core's plugin-facing
  surface a first-party plugin actually uses is published through
  `atlas_plugin_api`. Anything under `server.*` a plugin's non-test code
  imports is forbidden.
- `ALLOWED_CORE_TEST_SUBMODULES`: `server.apps.catalog.tests.factories`
  (test-entity builders) and `server.apps.catalog.models.audit`
  (`EntityAuditRecord`, asserting Core's own audit-trail side effect from a
  plugin's own admin test) stay allowlisted, test-only — first-party test
  fixtures/assertions a third-party plugin author's own tests wouldn't need
  a published contract for, symmetric with each other, not part of the
  contract surface itself. `server.apps.plugins.resolver` and
  `server.apps.plugins.runtime` are allowlisted the same way, for the
  search plugin's test that a disabled plugin runs none of its hooks.
- `ALLOWED_PLUGIN_TO_PLUGIN_EDGES`: a plugin importing another plugin's
  implementation modules directly, not through a declared contract-only
  package. Each remaining edge is documented as a known exception rather
  than silently allowed. Both are first-party test-fixture imports,
  symmetric with `ALLOWED_CORE_TEST_SUBMODULES`, not something a
  third-party plugin author's own tests would need a published contract
  for:
  `atlas_plugin_database_schema`'s own test suite (`tests/test_views.py`)
  imports `atlas_plugin_standard_catalog`'s `ResourceDetails` to build a
  fixture entity, and `atlas_plugin_flows`'s `tests/test_flow_query_event_
  steps.py` imports `atlas_plugin_apis`'s `ApiEndpoint`/`ApiOperation`
  directly to build fixture rows for its save-time-validation and
  read-time-ref-status tests, since ORM row construction needs the real
  model class, not a types-only contract.
- `DECLARED_CONTRACT_SUBMODULES`: a plugin's published contract-only
  submodule(s). An import of one of these is always allowed cross-plugin,
  independent of `ALLOWED_PLUGIN_TO_PLUGIN_EDGES`, which only documents
  *implementation* imports still outstanding. Two flavors:
  `.contracts` (types/schemas only, no Django models or business logic)
  for the pure type/schema edges, and `.extension_points` for the narrow
  function/registration surface an ORM-backed edge needs instead, since
  such an edge can't be fixed by moving types into a contract package —
  Django ORM querying needs the real model class. The owning plugin still
  owns every query against its own models itself; it's just reached
  through a function/extension-point call instead of an implementation
  import. For example:
  `atlas_plugin_apis.extension_points` exposes `due_for_spec_refresh()`,
  which Ingestion's periodic spec-refresh job calls instead of importing
  `ApiDetails`/`spec_fetch`, and a delete-guard that
  `atlas_plugin_standard_catalog` registers against it, an inversion of
  control that keeps `atlas_plugin_apis` from importing
  `atlas_plugin_standard_catalog` at all.
  `atlas_plugin_standard_catalog.extension_points` is the second:
  `atlas_plugin_apis`'s link-service view calls its `add_consumed_api()`
  instead of importing `ComponentDetails` directly, the same shape in the
  opposite direction. `atlas_plugin_ingestion.extension_points`
  is the third:
  `atlas_plugin_database_schema.plugin.register_runtime()` registers its
  own facet-writer against `atlas_plugin_ingestion`'s `facet_writers`
  extension point (the ADR 0014 mechanism `connectors`/`parsers` already
  use) instead of `atlas_plugin_ingestion` importing
  `atlas_plugin_database_schema` — this edge is the reverse of the other
  two (the *dependent* plugin reaches into the *owning* plugin's published
  registry, not the other way around), but it's the same "published,
  namespaced extension point" contract surface in every case.
  `atlas_plugin_flows`'s own pair is the fourth: `atlas_plugin_mcp`'s Flow
  tools (`list_flows`/`get_flow`) call `atlas_plugin_flows.extension_points.
  get_flow_service()` and reuse `atlas_plugin_flows.contracts.FlowIn`/
  `FlowPatch`/`FlowNotFoundError`, rather than importing `atlas_plugin_flows`'s
  `Flow` model or REST controllers directly — the same "published contract,
  not the owning plugin's implementation" shape every other entry here
  documents.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]
PLUGINS_ROOT = REPO_ROOT / "plugins"

# Core's de facto plugin-facing surface (see module docstring) — empty:
# every piece a plugin needs is published through `atlas_plugin_api` instead.
ALLOWED_CORE_SUBMODULES: tuple[str, ...] = ()
# Test-only (see module docstring), allowed only from a plugin's own
# `tests/` directory.
ALLOWED_CORE_TEST_SUBMODULES = (
    "server.apps.catalog.tests.factories",
    "server.apps.catalog.models.audit",
    # `atlas_plugin_search`'s `tests/test_inert.py` drives core's own runtime
    # phases to prove a disabled search plugin runs none of its hooks.
    "server.apps.plugins.resolver",
    "server.apps.plugins.runtime",
)

# Known plugin -> plugin implementation edges that predate this check
# (see module docstring). `(importing plugin id, imported package name)`.
# Two documented test-only fixture edges remain — see module docstring.
ALLOWED_PLUGIN_TO_PLUGIN_EDGES = frozenset(
    {
        ("database-schema", "atlas_plugin_standard_catalog"),
        # `atlas_plugin_flows`'s own test suite (`tests/test_flow_query_event_
        # steps.py`) imports `ApiEndpoint`/`ApiOperation` directly to build
        # fixture rows (create an Endpoint/Operation, then flip its `status`/
        # `deprecated`) for save-time validation
        # and read-time ref-status tests —
        # symmetric with the `database-schema` entry above: a first-party test
        # fixture import a third-party plugin author's own tests wouldn't need
        # a published contract for, not migrated onto `atlas_plugin_apis`'s
        # `.contracts`/`.extension_points` surface (ORM row construction needs
        # the real model class).
        ("flows", "atlas_plugin_apis"),
        # `atlas_plugin_mcp`'s own API-tool controller tests
        # (`tests/test_api_endpoint_controllers.py`) build `ApiEndpoint`/
        # `ApiOperation`/`Service*Usage` fixture rows and swap
        # `atlas_plugin_apis.permissions`'s policy evaluator to simulate a
        # denied user — same first-party-test-only rationale as the `flows`
        # entry above; the controllers themselves only ever import
        # `atlas_plugin_apis.extension_points`.
        ("mcp", "atlas_plugin_apis"),
    }
)

# A plugin's declared contract-only submodule(s) (see module docstring) —
# importing one of these from another plugin is always allowed, regardless
# of `ALLOWED_PLUGIN_TO_PLUGIN_EDGES`.
DECLARED_CONTRACT_SUBMODULES: dict[str, tuple[str, ...]] = {
    "atlas_plugin_standard_catalog": (
        "atlas_plugin_standard_catalog.contracts",
        "atlas_plugin_standard_catalog.extension_points",
    ),
    "atlas_plugin_apis": (
        "atlas_plugin_apis.contracts",
        "atlas_plugin_apis.extension_points",
    ),
    "atlas_plugin_ingestion": ("atlas_plugin_ingestion.extension_points",),
    "atlas_plugin_flows": (
        "atlas_plugin_flows.contracts",
        "atlas_plugin_flows.extension_points",
    ),
}

AUTHENTICATION_CONTRACT_SYMBOLS = frozenset(
    {
        "AuthenticationProviderContribution",
        "CredentialAuthenticationProvider",
        "RedirectAuthenticationProvider",
        "register_authentication_provider",
    }
)
"""Public symbols whose use marks a source file as provider implementation.

Authentication providers are trusted server code, but their supported
collaboration boundary is still ``atlas_plugin_api``. The marker keeps the
extra auth-specific rules scoped to provider modules rather than forbidding
ordinary plugins from using documented Django facilities they already own.
"""


def _is_authentication_provider_source(source_file: Path) -> bool:
    tree = ast.parse(source_file.read_text(), filename=str(source_file))
    return any(
        isinstance(node, ast.Name)
        and node.id in AUTHENTICATION_CONTRACT_SYMBOLS
        or isinstance(node, ast.Attribute)
        and node.attr in AUTHENTICATION_CONTRACT_SYMBOLS
        for node in ast.walk(tree)
    )


def _is_forbidden_authentication_import(module: str) -> bool:
    """Whether ``module`` bypasses the public provider/Core boundary."""

    if module == "server" or module.startswith("server."):
        return True
    if module == "django.conf.settings":
        return True
    if module in {"django.contrib.auth.login", "django.contrib.auth.logout"}:
        return True
    if module == "django.contrib.sessions" or module.startswith(
        "django.contrib.sessions."
    ):
        return True
    parts = module.split(".")
    return bool(parts and parts[0] == "allauth" and "internal" in parts[1:])


def _plugin_package_dirs() -> list[tuple[str, str, Path]]:
    """Each first-party plugin's `(plugin id, package name, package dir)`,
    e.g. `('ingestion', 'atlas_plugin_ingestion', .../plugins/ingestion/
    backend/atlas_plugin_ingestion)`."""
    found = []
    for plugin_dir in sorted(PLUGINS_ROOT.iterdir()):
        backend_dir = plugin_dir / "backend"
        if not backend_dir.is_dir():
            continue
        for candidate in sorted(backend_dir.iterdir()):
            if candidate.is_dir() and candidate.name.startswith(
                "atlas_plugin_"
            ):
                found.append((plugin_dir.name, candidate.name, candidate))
    return found


def _imported_modules(source_file: Path) -> list[str]:
    """Every dotted module path a file imports, from both `import x.y` and
    `from x.y import z` statements.

    `from x.y import z` yields `x.y.z`, not just `x.y`: `z` may itself be a
    submodule (`from server.apps.catalog import refs`) rather than an
    attribute, and prefix-matching the combined path against an allowlist
    of *submodules* handles both cases correctly — an attribute name tacked
    onto an already-allowed submodule prefix still matches that prefix.
    """
    tree = ast.parse(source_file.read_text(), filename=str(source_file))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif (
            isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
        ):
            modules.extend(
                f"{node.module}.{alias.name}" for alias in node.names
            )
    return modules


def _is_allowed_core_import(
    module: str, source_file: Path, package_dir: Path
) -> bool:
    if not (module == "server" or module.startswith("server.")):
        return True  # not a core import at all
    is_test_file = "tests" in source_file.relative_to(package_dir).parts
    allowed = ALLOWED_CORE_SUBMODULES + (
        ALLOWED_CORE_TEST_SUBMODULES if is_test_file else ()
    )
    return any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in allowed
    )


def _other_plugin_import(
    module: str, own_package: str, all_package_names: set[str]
) -> str | None:
    """The other plugin's package name, if `module` imports a *different*
    plugin's package; `None` if it imports its own package, `atlas_plugin_api`,
    or something that isn't a plugin package at all."""
    top = module.split(".", 1)[0]
    if top == own_package or top not in all_package_names:
        return None
    return top


def _is_declared_contract_import(module: str, other_package: str) -> bool:
    contract_submodules = DECLARED_CONTRACT_SUBMODULES.get(other_package, ())
    return any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in contract_submodules
    )


@pytest.mark.parametrize(
    ("plugin_id", "package_name", "package_dir"),
    _plugin_package_dirs(),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_plugin_does_not_import_forbidden_core_internals(
    plugin_id,
    package_name,
    package_dir,
):
    _ = plugin_id
    offenders = []
    for source_file in package_dir.rglob("*.py"):
        for module in _imported_modules(source_file):
            if not _is_allowed_core_import(module, source_file, package_dir):
                offenders.append(
                    f"{source_file.relative_to(REPO_ROOT)}: {module!r}"
                )

    assert offenders == [], (
        f"{package_name} imports core internals outside the allowed Core "
        f'surface (docs/plugin-architecture.md "Internal contract packages"): '
        + "; ".join(offenders)
    )


@pytest.mark.parametrize(
    ("plugin_id", "package_name", "package_dir"),
    _plugin_package_dirs(),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_plugin_does_not_import_another_plugins_implementation(
    plugin_id,
    package_name,
    package_dir,
):
    all_package_names = {name for _, name, _ in _plugin_package_dirs()}
    offenders = []
    for source_file in package_dir.rglob("*.py"):
        for module in _imported_modules(source_file):
            other = _other_plugin_import(
                module, package_name, all_package_names
            )
            if other is None:
                continue
            if _is_declared_contract_import(module, other):
                continue
            if (plugin_id, other) in ALLOWED_PLUGIN_TO_PLUGIN_EDGES:
                continue
            offenders.append(
                f"{source_file.relative_to(REPO_ROOT)}: {module!r}"
            )

    assert offenders == [], (
        f"{package_name} imports another plugin's implementation module "
        f"rather than a declared contract package: " + "; ".join(offenders)
    )


@pytest.mark.parametrize(
    ("plugin_id", "package_name", "package_dir"),
    _plugin_package_dirs(),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_authentication_plugins_use_only_the_published_provider_boundary(
    plugin_id,
    package_name,
    package_dir,
):
    offenders = []
    for source_file in package_dir.rglob("*.py"):
        if not _is_authentication_provider_source(source_file):
            continue
        for module in _imported_modules(source_file):
            if _is_forbidden_authentication_import(module):
                offenders.append(
                    f"{source_file.relative_to(REPO_ROOT)}: {module!r}"
                )

    assert offenders == [], (
        f"{package_name} authentication provider bypasses "
        f"`atlas.auth.providers.v1`; use the published `atlas_plugin_api` "
        f"contracts instead: " + "; ".join(offenders)
    )


@pytest.mark.parametrize(
    "module",
    [
        "server.apps.catalog.authentication.auth_providers",
        "server.settings.components.common.settings",
        "django.conf.settings",
        "django.contrib.auth.login",
        "django.contrib.auth.logout",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "allauth.account.internal.flows.login",
        "allauth.headless.internal.restkit.response",
        "allauth.socialaccount.internal.statekit",
    ],
)
def test_authentication_boundary_rejects_core_session_and_allauth_internals(
    module,
):
    assert _is_forbidden_authentication_import(module)


@pytest.mark.parametrize(
    "module",
    [
        "atlas_plugin_api.AuthenticationProviderDescriptor",
        "atlas_plugin_api.authentication.CredentialAuthenticationProvider",
        "django.http.HttpRequest",
        "allauth.socialaccount.providers.openid_connect.provider",
    ],
)
def test_authentication_boundary_allows_public_contracts_and_adapters(
    module,
):
    assert not _is_forbidden_authentication_import(module)
