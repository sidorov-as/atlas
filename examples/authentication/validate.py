"""Fast, image-free validation for the runnable authentication examples."""

from __future__ import annotations

import argparse
import ast
import configparser
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml
from atlas_composer.composition import check_plugin_config
from atlas_composer.lock import load_lock
from atlas_composer.manifest import load_manifest

ROOT = Path(__file__).resolve().parent
EXAMPLE_NAMES = (
    "local",
    "oidc-keycloak",
    "oauth2-gitea",
    "custom-credentials",
)
EXAMPLES = tuple(ROOT / name for name in EXAMPLE_NAMES)
SENSITIVE_ENV_NAME = re.compile(
    r"(?:PASSWORD|SECRET|TOKEN|PRIVATE_KEY|BIND_DN|CREDENTIAL)", re.IGNORECASE
)
FORBIDDEN_SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[oprsu]_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
}
ALLOWED_FIXTURE_PATHS = {
    Path("local/.env.example"),
    Path("oidc-keycloak/.env.example"),
    Path("oidc-keycloak/keycloak/realm.json"),
    Path("oauth2-gitea/.env.example"),
    Path("custom-credentials/.env.example"),
    Path("custom-credentials/plugin/tests/test_provider.py"),
}


def _text_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
    )


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text().splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected NAME=value")
        name, value = line.split("=", 1)
        if not name or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            raise ValueError(f"{path}:{line_number}: invalid environment name")
        if name in values:
            raise ValueError(f"{path}:{line_number}: duplicate {name}")
        if not value:
            raise ValueError(f"{path}:{line_number}: empty {name}")
        values[name] = value
    return values


def validate_syntax() -> None:
    for path in _text_files():
        if path.suffix in {".yaml", ".yml"}:
            if yaml.safe_load(path.read_text()) is None:
                raise ValueError(f"{path}: empty YAML document")
        elif path.suffix == ".json":
            json.loads(path.read_text())
        elif path.suffix == ".py":
            compile(path.read_text(), str(path), "exec")
        elif path.suffix == ".sh":
            subprocess.run(["bash", "-n", str(path)], check=True)
        elif path.name == ".env.example":
            _parse_env(path)
        elif path.suffix == ".ini":
            parser = configparser.ConfigParser()
            # Gitea permits global keys before its first INI section.
            parser.read_string("[DEFAULT]\n" + path.read_text())


def validate_schemas() -> None:
    plugin_roots = (
        ROOT.parents[1] / "plugins" / "auth-oidc" / "backend",
        ROOT.parents[1] / "plugins" / "auth-gitea" / "backend",
        ROOT / "custom-credentials" / "plugin",
    )
    for plugin_root in reversed(plugin_roots):
        sys.path.insert(0, str(plugin_root))
    from atlas_example_auth_fixture.plugin import PLUGIN as fixture_plugin
    from atlas_plugin_auth_gitea.plugin import PLUGIN as gitea_plugin
    from atlas_plugin_auth_oidc.plugin import PLUGIN as oidc_plugin

    descriptors = {
        plugin.id: plugin for plugin in (oidc_plugin, gitea_plugin, fixture_plugin)
    }
    for example in EXAMPLES:
        manifest = load_manifest(example / "manifest.yaml")
        lock = load_lock(example / "lock.yaml")
        check_plugin_config(manifest, descriptors)
        manifest_ids = [provider.id for provider in manifest.auth.providers]
        lock_ids = [provider.id for provider in lock.auth.providers]
        if manifest_ids != lock_ids:
            raise ValueError(
                f"{example.name}: manifest providers {manifest_ids!r} do not "
                f"match lock providers {lock_ids!r}"
            )
        if manifest.auth.default != lock.auth.default:
            raise ValueError(f"{example.name}: manifest and lock defaults do not match")


def validate_compose() -> None:
    for example in EXAMPLES:
        subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                ".env.example",
                "-f",
                "compose.yaml",
                "config",
                "--quiet",
            ],
            cwd=example,
            check=True,
        )


def validate_docs_commands() -> None:
    index = (ROOT / "README.md").read_text()
    for name, example in zip(EXAMPLE_NAMES, EXAMPLES, strict=True):
        if f"({name}/)" not in index and f"({name}/README.md)" not in index:
            raise ValueError(f"README.md: missing link to {name}/")
        readme = (example / "README.md").read_text()
        required = (
            "cp .env.example .env",
            "docker compose config --quiet",
            "docker compose up --build -d",
            "docker compose down --volumes --remove-orphans",
            "./smoke.sh",
        )
        for command in required:
            if command not in readme:
                raise ValueError(
                    f"{example / 'README.md'}: missing documented command {command!r}"
                )
        if not (example / "smoke.sh").is_file():
            raise ValueError(f"{example}: documented smoke.sh does not exist")


def _imported_top_levels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def validate_import_boundaries() -> None:
    package = ROOT / "custom-credentials" / "plugin" / "atlas_example_auth_fixture"
    allowed = {
        "__future__",
        "atlas_example_auth_fixture",
        "atlas_plugin_api",
        "dataclasses",
        "hmac",
        "pydantic",
        "typing",
    }
    offenders: list[str] = []
    for path in sorted(package.rglob("*.py")):
        for module in sorted(_imported_top_levels(path) - allowed):
            offenders.append(f"{path.relative_to(ROOT)}: {module}")
    if offenders:
        raise ValueError(
            "custom credential provider bypasses the public SDK boundary: "
            + "; ".join(offenders)
        )


def _declared_fixture_secrets() -> set[str]:
    values: set[str] = set()
    for example in EXAMPLES:
        for name, value in _parse_env(example / ".env.example").items():
            if SENSITIVE_ENV_NAME.search(name):
                values.add(value)
    realm = json.loads((ROOT / "oidc-keycloak" / "keycloak" / "realm.json").read_text())
    for user in realm.get("users", []):
        for credential in user.get("credentials", []):
            if credential.get("type") == "password":
                values.add(str(credential["value"]))
    return values


def validate_secrets() -> None:
    texts: dict[Path, str] = {}
    for path in _text_files():
        try:
            texts[path.relative_to(ROOT)] = path.read_text()
        except UnicodeDecodeError:
            continue

    errors: list[str] = []
    for path, content in texts.items():
        for label, pattern in FORBIDDEN_SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"{path}: contains a possible {label}")

    fixture_secrets = _declared_fixture_secrets()
    for secret in fixture_secrets:
        if not re.fullmatch(r"[a-z0-9-]+only-[A-Za-z0-9-]+", secret):
            errors.append(
                f"a checked-in sensitive fixture is not visibly disposable: {secret!r}"
            )
        for path, content in texts.items():
            if secret in content and path not in ALLOWED_FIXTURE_PATHS:
                errors.append(
                    f"{path}: contains disposable secret declared only for fixtures"
                )

    for path, content in texts.items():
        if path.suffix not in {".yaml", ".yml", ".py", ".json"}:
            continue
        if path in ALLOWED_FIXTURE_PATHS:
            continue
        for match in re.finditer(
            r"(?im)^\s*[\"']?[A-Za-z0-9_-]*(?:password|secret|token|private_key)"
            r"[A-Za-z0-9_-]*[\"']?\s*[:=]\s*[\"']([^\"'\s${}][^\"'\r\n]*)",
            content,
        ):
            errors.append(
                f"{path}: possible literal secret assignment {match.group(1)!r}"
            )

    if errors:
        raise ValueError("secret scan failed:\n- " + "\n- ".join(errors))


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_local_content() -> None:
    example = ROOT / "local"
    manifest = load_manifest(example / "manifest.yaml")
    lock = load_lock(example / "lock.yaml")

    _check(
        [provider.id for provider in manifest.auth.providers] == ["atlas.auth.local"],
        "local: manifest must select only atlas.auth.local",
    )
    _check(
        manifest.auth.default == "atlas.auth.local",
        "local: manifest default must be atlas.auth.local",
    )
    _check(
        manifest.auth.providers[0].signup == "disabled",
        "local: signup must be disabled",
    )
    _check(
        manifest.auth.public_origin == "http://localhost:18080",
        "local: public_origin must be http://localhost:18080",
    )
    _check(
        [provider.id for provider in lock.auth.providers] == ["atlas.auth.local"],
        "local: lock must select only atlas.auth.local",
    )
    _check(
        lock.auth.default == "atlas.auth.local",
        "local: lock default must be atlas.auth.local",
    )

    compose = yaml.safe_load((example / "compose.yaml").read_text())
    _check(
        compose["name"] == "atlas-auth-local",
        "local: compose name must be atlas-auth-local",
    )
    _check(
        set(compose["services"]) == {"postgres", "initializer", "backend", "frontend"},
        "local: compose must define exactly postgres/initializer/backend/frontend",
    )
    _check(
        "seed_admin" in " ".join(compose["services"]["initializer"]["command"]),
        "local: initializer command must run seed_admin",
    )
    _check(
        compose["services"]["postgres"]["volumes"]
        == ["local-postgres-data:/var/lib/postgresql/data"],
        "local: postgres volume must be local-postgres-data",
    )
    _check(
        compose["networks"]["database"]["internal"] is True,
        "local: database network must be internal",
    )


def validate_keycloak_content() -> None:
    example = ROOT / "oidc-keycloak"
    manifest = load_manifest(example / "manifest.yaml")
    lock = load_lock(example / "lock.yaml")

    _check(
        [provider.id for provider in manifest.auth.providers] == ["atlas.auth.oidc"],
        "oidc-keycloak: manifest must select only atlas.auth.oidc",
    )
    provider = manifest.auth.providers[0]
    _check(
        manifest.auth.default == "atlas.auth.oidc",
        "oidc-keycloak: manifest default must be atlas.auth.oidc",
    )
    _check(
        provider.principal_provisioning == "automatic",
        "oidc-keycloak: principal_provisioning must be automatic",
    )
    _check(
        provider.actor_provisioning == "automatic",
        "oidc-keycloak: actor_provisioning must be automatic",
    )
    _check(
        provider.group_sync.mode == "exact",
        "oidc-keycloak: group_sync.mode must be exact",
    )
    _check(
        provider.group_sync.mappings
        == {"atlas-platform": "oidc-platform", "atlas-readers": "oidc-readers"},
        "oidc-keycloak: group_sync.mappings do not match the documented mapping",
    )
    _check(
        provider.source_binding is not None,
        "oidc-keycloak: provider must declare a source_binding",
    )
    _check(
        [provider.id for provider in lock.auth.providers] == ["atlas.auth.oidc"],
        "oidc-keycloak: lock must select only atlas.auth.oidc",
    )
    _check(
        lock.auth.default == "atlas.auth.oidc",
        "oidc-keycloak: lock default must be atlas.auth.oidc",
    )
    _check(
        "oidc-client-only" not in (example / "lock.yaml").read_text(),
        "oidc-keycloak: lock.yaml must not reference oidc-client-only",
    )

    realm = json.loads((example / "keycloak" / "realm.json").read_text())
    client = next(
        item for item in realm["clients"] if item["clientId"] == "atlas-example"
    )
    groups_scope = next(
        item for item in realm["clientScopes"] if item["name"] == "groups"
    )
    _check(
        client["redirectUris"]
        == [
            "http://localhost:18080/auth/browser/v1/providers/atlas.auth.oidc/callback"
        ],
        "oidc-keycloak: realm.json client redirectUris do not match the gateway callback route",
    )
    _check(
        client["webOrigins"] == ["http://localhost:18080"],
        "oidc-keycloak: realm.json client webOrigins mismatch",
    )
    _check(
        client["secret"] == "${ATLAS_OIDC_CLIENT_SECRET}",
        "oidc-keycloak: realm.json client secret must reference ATLAS_OIDC_CLIENT_SECRET",
    )
    _check(
        "groups" in client["defaultClientScopes"],
        "oidc-keycloak: realm.json client must default to the groups scope",
    )
    _check(
        groups_scope["protocolMappers"][0]["config"]
        == {
            "claim.name": "groups",
            "full.path": "false",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
        "oidc-keycloak: realm.json groups scope mapper config mismatch",
    )
    _check(
        {item["username"] for item in realm["users"]} == {"oidc-alice", "oidc-bob"},
        "oidc-keycloak: realm.json must declare exactly oidc-alice and oidc-bob",
    )
    _check(
        {item["name"] for item in realm["groups"]}
        >= {"atlas-platform", "atlas-readers", "unmapped-upstream"},
        "oidc-keycloak: realm.json must declare the mapped and unmapped groups",
    )

    compose = yaml.safe_load((example / "compose.yaml").read_text())
    _check(
        compose["name"] == "atlas-auth-oidc-keycloak",
        "oidc-keycloak: compose name mismatch",
    )
    _check(
        set(compose["services"])
        == {"postgres", "keycloak", "initializer", "backend", "frontend"},
        "oidc-keycloak: compose service set mismatch",
    )
    _check(
        compose["services"]["keycloak"]["image"] == "quay.io/keycloak/keycloak:26.4.5",
        "oidc-keycloak: keycloak image must be pinned to 26.4.5",
    )
    _check(
        compose["services"]["keycloak"]["healthcheck"],
        "oidc-keycloak: keycloak service must declare a healthcheck",
    )
    _check(
        compose["services"]["initializer"]["depends_on"]["keycloak"]
        == {"condition": "service_healthy"},
        "oidc-keycloak: initializer must wait for keycloak to be healthy",
    )
    _check(
        compose["services"]["postgres"]["volumes"]
        == ["oidc-postgres-data:/var/lib/postgresql/data"],
        "oidc-keycloak: postgres volume mismatch",
    )
    _check(
        compose["services"]["keycloak"]["volumes"][1]
        == "oidc-keycloak-data:/opt/keycloak/data",
        "oidc-keycloak: keycloak data volume mismatch",
    )
    _check(
        compose["networks"]["database"]["internal"] is True,
        "oidc-keycloak: database network must be internal",
    )

    smoke = (example / "browser_smoke.py").read_text()
    for required in (
        "/providers/{PROVIDER_ID}/start",
        "kc-form-login",
        '"principalCount": 1',
        '"groups": ["oidc-platform"]',
        '"groups": []',
        "present=False",
        "expected=403",
        "/auth/browser/v1/session",
        'provider["flowKind"] != "credentials"',
    ):
        _check(
            required in smoke,
            f"oidc-keycloak: browser_smoke.py missing required check {required!r}",
        )


def validate_gitea_content() -> None:
    example = ROOT / "oauth2-gitea"
    manifest = load_manifest(example / "manifest.yaml")
    lock = load_lock(example / "lock.yaml")

    _check(
        [provider.id for provider in manifest.auth.providers] == ["atlas.auth.gitea"],
        "oauth2-gitea: manifest must select only atlas.auth.gitea",
    )
    provider = manifest.auth.providers[0]
    _check(
        manifest.auth.default == "atlas.auth.gitea",
        "oauth2-gitea: manifest default must be atlas.auth.gitea",
    )
    _check(
        provider.principal_provisioning == "automatic",
        "oauth2-gitea: principal_provisioning must be automatic",
    )
    _check(
        provider.actor_provisioning == "automatic",
        "oauth2-gitea: actor_provisioning must be automatic",
    )
    _check(
        provider.group_sync.mode == "none", "oauth2-gitea: group_sync.mode must be none"
    )
    _check(
        provider.group_sync.mappings == {},
        "oauth2-gitea: group_sync.mappings must be empty",
    )
    _check(
        provider.source_binding is not None,
        "oauth2-gitea: provider must declare a source_binding",
    )
    _check(
        provider.source_binding.source_id == "http://gitea.localhost:18082",
        "oauth2-gitea: source_binding.source_id mismatch",
    )
    _check(
        [provider.id for provider in lock.auth.providers] == ["atlas.auth.gitea"],
        "oauth2-gitea: lock must select only atlas.auth.gitea",
    )
    _check(
        lock.auth.default == "atlas.auth.gitea",
        "oauth2-gitea: lock default must be atlas.auth.gitea",
    )
    lock_text = (example / "lock.yaml").read_text()
    _check(
        "client_secret" not in lock_text,
        "oauth2-gitea: lock.yaml must not contain a literal client_secret",
    )
    gitea_plugin = lock.plugins["atlas.auth.gitea@0.1.0"]
    _check(
        gitea_plugin.config["clientSecret"] == {"fromEnv": "GITEA_CLIENT_SECRET"},
        "oauth2-gitea: locked clientSecret must come fromEnv GITEA_CLIENT_SECRET",
    )

    bootstrap = (example / "gitea" / "bootstrap_oauth.py").read_text()
    env_example = (example / ".env.example").read_text()
    for required in (
        "/api/v1/user/applications/oauth2",
        "client_secret",
        "/run/atlas-auth/gitea.env",
        "http://localhost:18080/auth/browser/v1/providers/",
    ):
        _check(
            required in bootstrap,
            f"oauth2-gitea: bootstrap_oauth.py missing {required!r}",
        )
    _check(
        "GITEA_CLIENT_SECRET=" not in env_example,
        "oauth2-gitea: .env.example must not commit a runtime OAuth secret",
    )

    compose = yaml.safe_load((example / "compose.yaml").read_text())
    _check(
        compose["name"] == "atlas-auth-oauth2-gitea",
        "oauth2-gitea: compose name mismatch",
    )
    _check(
        set(compose["services"])
        == {
            "postgres",
            "gitea",
            "gitea-users",
            "oauth-bootstrap",
            "initializer",
            "backend",
            "frontend",
        },
        "oauth2-gitea: compose service set mismatch",
    )
    _check(
        compose["services"]["gitea"]["image"] == "gitea/gitea:1.27.3",
        "oauth2-gitea: gitea image must be pinned",
    )
    _check(
        compose["services"]["gitea"]["healthcheck"],
        "oauth2-gitea: gitea service must declare a healthcheck",
    )
    _check(
        compose["services"]["gitea-users"]["depends_on"]["gitea"]
        == {"condition": "service_healthy"},
        "oauth2-gitea: gitea-users must wait for gitea to be healthy",
    )
    _check(
        compose["services"]["oauth-bootstrap"]["depends_on"]["gitea-users"]
        == {"condition": "service_completed_successfully"},
        "oauth2-gitea: oauth-bootstrap must wait for gitea-users to complete",
    )
    _check(
        compose["services"]["initializer"]["depends_on"]["oauth-bootstrap"]
        == {"condition": "service_completed_successfully"},
        "oauth2-gitea: initializer must wait for oauth-bootstrap to complete",
    )
    _check(
        compose["networks"]["database"]["internal"] is True,
        "oauth2-gitea: database network must be internal",
    )
    _check(
        "gitea-runtime-secrets:/run/atlas-auth:ro"
        in compose["services"]["backend"]["volumes"],
        "oauth2-gitea: backend must mount the gitea runtime secrets volume read-only",
    )

    smoke = (example / "browser_smoke.py").read_text()
    for required in (
        "/providers/{PROVIDER_ID}/start",
        'consent_values["granted"] = "true"',
        'state["subject"].isdigit()',
        'state["providerGrants"] == 0',
        'state["isStaff"] is False',
        'state["isSuperuser"] is False',
        "expected=403",
        "/auth/browser/v1/session",
        "assert atlas_state(env_file, username) == state",
    ):
        _check(
            required in smoke, f"oauth2-gitea: browser_smoke.py missing {required!r}"
        )


def validate_custom_credentials_content() -> None:
    example = ROOT / "custom-credentials"
    manifest = load_manifest(example / "manifest.yaml")
    lock = load_lock(example / "lock.yaml")

    _check(
        [provider.id for provider in manifest.auth.providers]
        == ["example.auth.fixture", "atlas.auth.local"],
        "custom-credentials: manifest must select the fixture then the local fallback",
    )
    fixture = manifest.auth.providers[0]
    _check(
        manifest.auth.default == "example.auth.fixture",
        "custom-credentials: manifest default must be the fixture",
    )
    _check(
        fixture.principal_provisioning == "automatic",
        "custom-credentials: principal_provisioning must be automatic",
    )
    _check(
        fixture.actor_provisioning == "automatic",
        "custom-credentials: actor_provisioning must be automatic",
    )
    _check(
        fixture.group_sync.mode == "exact",
        "custom-credentials: group_sync.mode must be exact",
    )
    _check(
        fixture.group_sync.mappings == {"fixture-platform": "custom-platform"},
        "custom-credentials: group_sync.mappings mismatch",
    )
    _check(
        [provider.id for provider in lock.auth.providers]
        == ["example.auth.fixture", "atlas.auth.local"],
        "custom-credentials: lock must select the fixture then the local fallback",
    )
    locked_plugin = lock.plugins["example.auth.fixture@0.1.0"]
    _check(
        locked_plugin.config["fixturePassword"]
        == {"fromEnv": "ATLAS_FIXTURE_PASSWORD"},
        "custom-credentials: locked fixturePassword must come fromEnv ATLAS_FIXTURE_PASSWORD",
    )
    lock_text = (example / "lock.yaml").read_text()
    # Compared against the real declared value, not a copied-in literal: a
    # hardcoded secret-shaped string here would itself trip this file's own
    # `secrets` check, since validate.py lives under the tree that check scans.
    fixture_secret = _parse_env(example / ".env.example").get("ATLAS_FIXTURE_PASSWORD")
    _check(
        bool(fixture_secret) and fixture_secret not in lock_text,
        "custom-credentials: lock.yaml must not contain the disposable fixture password",
    )

    compose = yaml.safe_load((example / "compose.yaml").read_text())
    _check(
        compose["name"] == "atlas-auth-custom-credentials",
        "custom-credentials: compose name mismatch",
    )
    _check(
        set(compose["services"]) == {"postgres", "initializer", "backend", "frontend"},
        "custom-credentials: compose must define exactly postgres/initializer/backend/frontend",
    )
    _check(
        compose["services"]["postgres"]["volumes"]
        == ["custom-credentials-postgres-data:/var/lib/postgresql/data"],
        "custom-credentials: postgres volume mismatch",
    )
    _check(
        compose["networks"]["database"]["internal"] is True,
        "custom-credentials: database network must be internal",
    )
    _check(
        "openldap" not in (example / "compose.yaml").read_text().lower(),
        "custom-credentials: compose must stay LDAP-free (fixture only, no real LDAP server)",
    )

    mapping = (example / "LDAP-MAPPING.md").read_text()
    package = example / "plugin"
    for public_type in (
        "CredentialAuthenticationProvider",
        "CredentialFlowContext",
        "CredentialInput",
        "VerifiedIdentity",
        "AssuredAttribute",
        "ExternalGroupSnapshot",
        "AuthenticationFailure",
    ):
        _check(
            public_type in mapping,
            f"custom-credentials: LDAP-MAPPING.md missing {public_type!r}",
        )
    _check(
        "atlas_plugin_api" in mapping,
        "custom-credentials: LDAP-MAPPING.md must name atlas_plugin_api",
    )
    _check(
        not any("ldap" in path.name.lower() for path in package.rglob("*")),
        "custom-credentials: plugin package must not name any LDAP-specific file",
    )

    smoke = (example / "smoke.py").read_text()
    for required in (
        '"fixture-alice", "", expected=400',
        "does-not-exist",
        "fixture-provider-outage",
        "LOCAL_PROVIDER",
        '"groups": ["custom-platform"]',
        "finiteExpiry",
        "fixture-groups-unavailable",
        "expected=403",
        "fixture_password not in logs",
        "/auth/browser/v1/session",
    ):
        _check(required in smoke, f"custom-credentials: smoke.py missing {required!r}")


def validate_content() -> None:
    validate_local_content()
    validate_keycloak_content()
    validate_gitea_content()
    validate_custom_credentials_content()


INTEGRATION_WORKFLOW = (
    ROOT.parents[1]
    / ".github"
    / "workflows"
    / "authentication-examples-integration.yml"
)


def validate_integration_workflow() -> None:
    workflow = yaml.safe_load(INTEGRATION_WORKFLOW.read_text())
    job = workflow["jobs"]["integration"]
    _check(
        job["strategy"]["fail-fast"] is False,
        "integration workflow: fail-fast must be false",
    )
    _check(
        tuple(job["strategy"]["matrix"]["example"]) == EXAMPLE_NAMES,
        "integration workflow: matrix must cover every example, in order",
    )
    _check(
        "continue-on-error" not in job,
        "integration workflow: the integration job must not ignore failures",
    )

    steps = {step["name"]: step for step in job["steps"] if "name" in step}
    _check(
        steps["Start topology"]["run"].startswith("docker compose"),
        "integration workflow: Start topology must use docker compose",
    )
    _check(
        "ci.py run" in steps["Run topology smoke test"]["run"],
        "integration workflow: smoke step must call ci.py run",
    )
    _check(
        steps["Collect redacted diagnostics"]["if"] == "always()",
        "integration workflow: diagnostics must always run",
    )
    _check(
        "ci.py collect" in steps["Collect redacted diagnostics"]["run"],
        "integration workflow: diagnostics step must call ci.py collect",
    )
    _check(
        steps["Stop topology"]["if"] == "always()",
        "integration workflow: topology teardown must always run",
    )
    _check(
        "--volumes --remove-orphans" in steps["Stop topology"]["run"],
        "integration workflow: teardown must remove volumes and orphans",
    )
    _check(
        steps["Upload redacted diagnostics"]["if"] == "always()",
        "integration workflow: diagnostics upload must always run",
    )
    _check(
        steps["Upload redacted diagnostics"]["with"]["retention-days"] == 7,
        "integration workflow: diagnostics retention must be 7 days",
    )

    browser_job = workflow["jobs"]["integration"]
    negative_job = workflow["jobs"]["security-negative-journeys"]
    command = next(
        step["run"]
        for step in negative_job["steps"]
        if step.get("name") == "Run authentication security-negative journeys"
    )
    _check(
        browser_job["name"].startswith("Release browser gate"),
        "integration workflow: browser job must be named as a release gate",
    )
    _check(
        tuple(browser_job["strategy"]["matrix"]["example"]) == EXAMPLE_NAMES,
        "integration workflow: browser gate matrix must cover every example, in order",
    )
    for required in (
        "test_admin_password_login_defaults_to_disabled",
        "test_inactive_principal_is_rejected_on_the_next_session_request",
        "test_source_fingerprint_change_requires_reviewed_migration",
        "test_restricted_policy_rejects_unverified_email_without_creating_state",
        "test_incomplete_exact_snapshot_rolls_back_and_failure_event_survives",
        "test_concurrent_first_login_creates_one_identity_and_actor",
        "test_legacy_oidc_grant_can_transfer_without_residual_manual_access",
    ):
        _check(
            required in command,
            f"integration workflow: security-negative-journeys must run {required!r}",
        )


def validate_ci_helper() -> None:
    import ci

    # Built from parts rather than one contiguous literal: a real JWT-shaped
    # string here would itself trip this file's own `secrets` check, since
    # validate.py lives under the tree that check scans.
    jwt_like = "eyJaaa" + "." + "bbb" + "." + "ccc"
    raw = (
        "Authorization: Bearer upstream-token\n"
        "Cookie: sessionid=session-value; csrftoken=csrf-value\n"
        "GITEA_CLIENT_SECRET=generated-secret\n"
        "callback=/callback?code=oauth-code&state=oauth-state\n"
        f'payload={{"password":"fixture-password","id_token":"{jwt_like}"}}\n'
    )
    safe = ci.redact(
        raw, secrets=("upstream-token", "session-value", "fixture-password")
    )
    for secret in (
        "upstream-token",
        "session-value",
        "csrf-value",
        "generated-secret",
        "oauth-code",
        "oauth-state",
        "fixture-password",
        jwt_like,
    ):
        _check(secret not in safe, f"ci.redact() failed to scrub {secret!r}")
    _check("<redacted>" in safe, "ci.redact() did not emit a redaction marker")


def validate_workflows() -> None:
    validate_integration_workflow()
    validate_ci_helper()


DOCS_SITE_DOCS = ROOT.parents[1] / "docs-site" / "docs"
FIXTURE_PACKAGE = ROOT / "custom-credentials" / "plugin" / "atlas_example_auth_fixture"
FIXTURE_PLUGIN_SOURCE = FIXTURE_PACKAGE / "plugin.py"
FIXTURE_CONFIG_SOURCE = FIXTURE_PACKAGE / "config.py"
# The docs-site pages allowed to describe authentication (mirrors
# docs-site/scripts/validate_docs.py's AUTH_NAV_PAGES); only the fixture's
# own slice of doc accuracy is checked here, not the whole set docs-site owns.
FIXTURE_DOC_PAGES = (
    "operating-atlas/authentication.md",
    "operating-atlas/local-authentication.md",
    "operating-atlas/oidc-authentication.md",
    "operating-atlas/gitea-authentication.md",
    "operating-atlas/identity-provisioning.md",
    "operating-atlas/group-reconciliation.md",
    "operating-atlas/authentication-security.md",
    "operating-atlas/authentication-migration.md",
    "plugin-development/authentication-provider-sdk.md",
    "reference/authentication.md",
)
FIXTURE_PROVIDER_ID_REFERENCE = re.compile(r"\bexample\.auth\.[a-z][a-z0-9.-]*\b")
DOC_YAML_FENCE = re.compile(r"```ya?ml[^\n]*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def _fixture_provider_id() -> str:
    tree = ast.parse(
        FIXTURE_PLUGIN_SOURCE.read_text(), filename=str(FIXTURE_PLUGIN_SOURCE)
    )
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"PROVIDER_ID", "LOCAL_PROVIDER_ID"}
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise ValueError(
        f"{FIXTURE_PLUGIN_SOURCE}: no PROVIDER_ID/LOCAL_PROVIDER_ID literal found"
    )


def _fixture_config_fields() -> set[str]:
    tree = ast.parse(
        FIXTURE_CONFIG_SOURCE.read_text(), filename=str(FIXTURE_CONFIG_SOURCE)
    )
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "FixtureCredentialConfig":
            continue
        fields: set[str] = set()
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(
                statement.target, ast.Name
            ):
                continue
            name = statement.target.id
            if isinstance(statement.value, ast.Call):
                for keyword in statement.value.keywords:
                    if (
                        keyword.arg == "alias"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        name = keyword.value.value
                        break
            fields.add(name)
        return fields
    raise ValueError(
        f"{FIXTURE_CONFIG_SOURCE}: class FixtureCredentialConfig was not found"
    )


def validate_docs_accuracy() -> None:
    """Doc-accuracy check scoped to the fixture, mirroring what
    docs-site/scripts/validate_docs.py's PROVIDER_SOURCES/PROVIDER_CONFIG_SOURCES
    fixture entries checked before they moved here (see 1.4 in tasks.md)."""
    provider_id = _fixture_provider_id()
    fields = _fixture_config_fields()

    doc_paths = [
        DOCS_SITE_DOCS / relative
        for relative in FIXTURE_DOC_PAGES
        if (DOCS_SITE_DOCS / relative).is_file()
    ]
    doc_paths += sorted(ROOT.glob("*/README.md"))

    for path in doc_paths:
        text = path.read_text()
        for reference in sorted(set(FIXTURE_PROVIDER_ID_REFERENCE.findall(text))):
            _check(
                reference == provider_id,
                f"{path}: references unknown fixture provider id {reference!r}, "
                f"source declares {provider_id!r}",
            )
        for index, source in enumerate(DOC_YAML_FENCE.findall(text), start=1):
            try:
                value = yaml.safe_load(source)
            except yaml.YAMLError:
                continue
            if not isinstance(value, dict):
                continue
            plugins = value.get("plugins", [])
            if not isinstance(plugins, list):
                continue
            for plugin in plugins:
                if not isinstance(plugin, dict) or plugin.get("id") != provider_id:
                    continue
                config = plugin.get("config", {})
                if not isinstance(config, dict):
                    continue
                unknown = sorted(set(config) - fields)
                _check(
                    not unknown,
                    f"{path}: YAML snippet {index} configures {provider_id} with "
                    f"fields absent from FixtureCredentialConfig: {unknown}",
                )


CHECKS = {
    "syntax": validate_syntax,
    "schemas": validate_schemas,
    "compose": validate_compose,
    "docs": validate_docs_commands,
    "imports": validate_import_boundaries,
    "secrets": validate_secrets,
    "content": validate_content,
    "workflows": validate_workflows,
    "docs-accuracy": validate_docs_accuracy,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=(*CHECKS, "all"))
    args = parser.parse_args(argv)
    selected = (
        CHECKS.items() if args.check == "all" else ((args.check, CHECKS[args.check]),)
    )
    for name, check in selected:
        check()
        print(f"authentication examples: {name} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
