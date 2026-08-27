"""Validate Atlas-specific documentation contracts before the site build."""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from urllib.parse import unquote, urlsplit

import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DOCS = ROOT / "docs"
NAV = ROOT / "zensical.toml"
MANIFEST = REPO / "distributions" / "default" / "manifest.yaml"
EXAMPLES = ROOT / "examples" / "first-plugin" / "first-plugin-backend"
AUTH_EXAMPLES = REPO / "examples" / "authentication"
MANIFEST_SOURCE = REPO / "composer" / "atlas_composer" / "manifest.py"
AUTH_URLS_SOURCE = (
    REPO / "core" / "backend" / "server" / "apps" / "catalog" / "auth_urls.py"
)
PROVIDER_SOURCES = (
    REPO / "core" / "backend" / "server" / "apps" / "catalog" / "auth_descriptors.py",
    REPO / "plugins" / "auth-oidc" / "backend" / "atlas_plugin_auth_oidc" / "plugin.py",
    REPO
    / "plugins"
    / "auth-gitea"
    / "backend"
    / "atlas_plugin_auth_gitea"
    / "plugin.py",
    AUTH_EXAMPLES
    / "custom-credentials"
    / "plugin"
    / "atlas_example_auth_fixture"
    / "plugin.py",
)
PROVIDER_CONFIG_SOURCES = {
    "atlas.auth.oidc": (
        REPO
        / "plugins"
        / "auth-oidc"
        / "backend"
        / "atlas_plugin_auth_oidc"
        / "config.py",
        "OIDCConfig",
    ),
    "atlas.auth.gitea": (
        REPO
        / "plugins"
        / "auth-gitea"
        / "backend"
        / "atlas_plugin_auth_gitea"
        / "config.py",
        "GiteaConfig",
    ),
    "example.auth.fixture": (
        AUTH_EXAMPLES
        / "custom-credentials"
        / "plugin"
        / "atlas_example_auth_fixture"
        / "config.py",
        "FixtureCredentialConfig",
    ),
}
AUTH_NAV_PAGES = {
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
}
AUTH_MANIFEST_MODELS = {
    "auth": "AuthConfig",
    "provider": "AuthProviderEntry",
    "groupSync": "GroupSyncConfig",
    "sourceBinding": "SourceBindingConfig",
    "restrictedAttribute": "RestrictedAttributeRequirement",
    "adminPassword": "AdminPasswordConfig",
    "outboundTrust": "OutboundTrustConfig",
    "passwordPolicy": "PasswordPolicyConfig",
    "recovery": "RecoveryPolicyConfig",
}

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
FEATURE_ID = re.compile(r"^plugin-id:\s*([^\s#]+)\s*$", re.MULTILINE)
PLUGIN_ID = re.compile(r"^\s*- id:\s*([^\s#]+)\s*$", re.MULTILINE)
YAML_FENCE = re.compile(r"```ya?ml[^\n]*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
PROVIDER_ID_REFERENCE = re.compile(
    r"\b(?:atlas\.auth\.[a-z][a-z0-9.-]*|example\.auth\.[a-z][a-z0-9.-]*)\b"
)
ENV_REFERENCE = re.compile(
    r"`((?:ATLAS|OIDC|GITEA|DJANGO|POSTGRES|KC)_[A-Z][A-Z0-9_]*)`"
)
ENV_NAME = re.compile(r"\b(?:ATLAS|OIDC|GITEA|DJANGO|POSTGRES|KC)_[A-Z][A-Z0-9_]*\b")
GATEWAY_PATH = re.compile(r"/auth/browser/v1(?:/[A-Za-z0-9._{}?=&%/-]+)?")
GITHUB_REPO_PREFIX = "https://github.com/sidorov-as/atlas/"


def fail(errors: list[str], path: Path, message: str) -> None:
    try:
        display = path.relative_to(ROOT)
    except ValueError:
        try:
            display = path.relative_to(REPO)
        except ValueError:
            display = path
    errors.append(f"{display}: {message}")


def front_matter(path: Path, errors: list[str]) -> str:
    match = FRONT_MATTER.match(path.read_text())
    if match is None:
        return ""
    for required in ("title:", "description:", "audience:", "page-type:"):
        if required not in match.group(1):
            fail(errors, path, f"front matter is missing {required[:-1]!r}")
    return match.group(1)


def _literal_assignment(path: Path, names: set[str]) -> dict[str, str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id in names
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            values[target.id] = node.value.value
    return values


def source_provider_ids() -> set[str]:
    provider_ids: set[str] = set()
    for path in PROVIDER_SOURCES:
        values = _literal_assignment(path, {"PROVIDER_ID", "LOCAL_PROVIDER_ID"})
        provider_ids.update(values.values())
    return provider_ids


def source_model_fields(path: Path, class_name: str) -> set[str]:
    """Read accepted serialized field names from a Pydantic model source."""

    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        fields: set[str] = set()
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(
                statement.target, ast.Name
            ):
                continue
            serialized_name = statement.target.id
            if isinstance(statement.value, ast.Call):
                for keyword in statement.value.keywords:
                    if (
                        keyword.arg == "alias"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        serialized_name = keyword.value.value
                        break
            fields.add(serialized_name)
        return fields
    raise ValueError(f"class {class_name!r} was not found in {path}")


def source_manifest_fields() -> dict[str, set[str]]:
    return {
        name: source_model_fields(MANIFEST_SOURCE, model)
        for name, model in AUTH_MANIFEST_MODELS.items()
    }


def source_provider_config_fields() -> dict[str, set[str]]:
    return {
        provider_id: source_model_fields(path, model)
        for provider_id, (path, model) in PROVIDER_CONFIG_SOURCES.items()
    }


def source_gateway_routes() -> set[str]:
    """Extract the public gateway paths from Django's URL source."""

    tree = ast.parse(AUTH_URLS_SOURCE.read_text(), filename=str(AUTH_URLS_SOURCE))
    # The include prefix is itself a documented namespace even though Django
    # intentionally serves no index view at that exact path.
    routes: set[str] = {"/auth/browser/v1"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "path" or not node.args:
            continue
        route = node.args[0]
        if isinstance(route, ast.Constant) and isinstance(route.value, str):
            normalized = re.sub(
                r"<[^:>]+:([^>]+)>",
                r"{\1}",
                route.value.rstrip("/"),
            )
            routes.add(f"/auth/browser/v1/{normalized}".rstrip("/"))
    return routes


def _walk_nav(value: object) -> Iterable[str]:
    if isinstance(value, str) and value.endswith(".md"):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _walk_nav(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_nav(child)


def validate_navigation(errors: list[str]) -> None:
    data = tomllib.loads(NAV.read_text())
    nav_pages = set(_walk_nav(data.get("project", {}).get("nav", [])))
    for relative in sorted(nav_pages):
        if not (DOCS / relative).is_file():
            fail(errors, NAV, f"navigation target {relative!r} does not exist")
    for relative in sorted(AUTH_NAV_PAGES - nav_pages):
        fail(errors, DOCS / relative, "authentication page is missing from navigation")


def _unknown_keys(
    errors: list[str], path: Path, label: str, value: object, allowed: set[str]
) -> None:
    if not isinstance(value, Mapping):
        fail(errors, path, f"{label} must be a YAML mapping")
        return
    unknown = sorted(set(value) - allowed)
    if unknown:
        fail(errors, path, f"{label} uses fields absent from source schema: {unknown}")


def validate_auth_mapping(
    errors: list[str],
    path: Path,
    auth: object,
    fields: dict[str, set[str]],
    provider_ids: set[str],
) -> None:
    _unknown_keys(errors, path, "auth snippet", auth, fields["auth"])
    if not isinstance(auth, Mapping):
        return
    providers = auth.get("providers", [])
    if not isinstance(providers, list):
        fail(errors, path, "auth.providers must be a YAML list")
        return
    selected: list[str] = []
    for provider in providers:
        _unknown_keys(
            errors, path, "auth provider snippet", provider, fields["provider"]
        )
        if not isinstance(provider, Mapping):
            continue
        provider_id = provider.get("id")
        if isinstance(provider_id, str):
            selected.append(provider_id)
            if provider_id not in provider_ids:
                fail(
                    errors, path, f"unknown authentication provider id {provider_id!r}"
                )
        nested = (
            ("groupSync", "groupSync"),
            ("sourceBinding", "sourceBinding"),
        )
        for key, model in nested:
            if key in provider:
                _unknown_keys(errors, path, key, provider[key], fields[model])
        requirements = provider.get("restrictedAttributes", [])
        if isinstance(requirements, list):
            for requirement in requirements:
                _unknown_keys(
                    errors,
                    path,
                    "restrictedAttributes entry",
                    requirement,
                    fields["restrictedAttribute"],
                )
    default = auth.get("default")
    if isinstance(default, str) and selected and default not in selected:
        fail(errors, path, f"auth.default {default!r} is not selected in the snippet")
    for key in ("adminPassword", "outboundTrust", "passwordPolicy", "recovery"):
        if key in auth:
            _unknown_keys(errors, path, key, auth[key], fields[key])


def validate_yaml_snippets(
    errors: list[str],
    paths: Iterable[Path],
    fields: dict[str, set[str]],
    provider_ids: set[str],
    provider_config_fields: dict[str, set[str]],
) -> None:
    for path in paths:
        for index, source in enumerate(YAML_FENCE.findall(path.read_text()), start=1):
            try:
                value = yaml.safe_load(source)
            except yaml.YAMLError as exc:
                fail(errors, path, f"YAML snippet {index} does not parse: {exc}")
                continue
            if not isinstance(value, Mapping):
                continue
            if "auth" in value:
                validate_auth_mapping(errors, path, value["auth"], fields, provider_ids)
            plugins = value.get("plugins", [])
            if not isinstance(plugins, list):
                continue
            for plugin in plugins:
                if not isinstance(plugin, Mapping):
                    continue
                provider_id = plugin.get("id")
                if provider_id in provider_config_fields and "config" in plugin:
                    _unknown_keys(
                        errors,
                        path,
                        f"{provider_id} config snippet",
                        plugin["config"],
                        provider_config_fields[provider_id],
                    )


def source_environment_names() -> set[str]:
    roots = (
        REPO / "core" / "backend",
        REPO / "composer",
        REPO / "plugins" / "auth-oidc",
        REPO / "plugins" / "auth-gitea",
        AUTH_EXAMPLES,
        REPO / "distributions" / "default",
    )
    names: set[str] = set()
    suffixes = {".py", ".yaml", ".yml", ".json", ".sh", ".env", ".example"}
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if "generated" in path.parts or path.name.endswith(".md"):
                continue
            try:
                names.update(ENV_NAME.findall(path.read_text()))
            except UnicodeDecodeError:
                continue
    return names


def _normalize_gateway_path(value: str, provider_ids: set[str]) -> str:
    path = unquote(value).split("?", 1)[0].rstrip("/")
    for provider_id in provider_ids:
        path = path.replace(f"/providers/{provider_id}/", "/providers/{provider_id}/")
    return path


def validate_source_references(
    errors: list[str],
    paths: Iterable[Path],
    provider_ids: set[str],
    environment_names: set[str],
    routes: set[str],
) -> None:
    for path in paths:
        text = path.read_text()
        for provider_id in sorted(set(PROVIDER_ID_REFERENCE.findall(text))):
            if provider_id == "atlas.auth.providers.v1":
                continue
            if provider_id not in provider_ids:
                fail(
                    errors,
                    path,
                    f"provider id {provider_id!r} has no source descriptor",
                )
        for name in sorted(set(ENV_REFERENCE.findall(text)) - environment_names):
            fail(
                errors,
                path,
                f"environment name {name!r} is absent from source/example contracts",
            )
        for documented in sorted(set(GATEWAY_PATH.findall(text))):
            normalized = _normalize_gateway_path(documented, provider_ids)
            if normalized not in routes:
                fail(
                    errors,
                    path,
                    f"gateway route {documented!r} is absent from Django URL contracts",
                )


def _link_target(path: Path, raw_target: str) -> Path | None:
    target = raw_target.strip("<>")
    parsed = urlsplit(target)
    if parsed.scheme in {"http", "https"}:
        if not target.startswith(GITHUB_REPO_PREFIX):
            return None
        repository_path = parsed.path.split("/atlas/", 1)[-1]
        for prefix in ("tree/main/", "blob/main/"):
            repository_path = repository_path.removeprefix(prefix)
        return REPO / unquote(repository_path)
    if parsed.scheme or target.startswith(("#", "/")):
        return None
    return (path.parent / unquote(parsed.path)).resolve()


def validate_links(errors: list[str], paths: Iterable[Path]) -> None:
    for path in paths:
        for target in MARKDOWN_LINK.findall(path.read_text()):
            resolved = _link_target(path, target)
            if resolved is not None and not resolved.exists():
                fail(errors, path, f"link target {target!r} does not exist")


def authentication_document_paths() -> list[Path]:
    docs = [DOCS / relative for relative in sorted(AUTH_NAV_PAGES)]
    examples = sorted(AUTH_EXAMPLES.rglob("README.md"))
    return docs + examples


def main() -> int:
    errors: list[str] = []
    feature_ids: dict[str, Path] = {}
    markdown_files = sorted(DOCS.rglob("*.md"))
    nav_text = NAV.read_text()

    for path in markdown_files:
        metadata = front_matter(path, errors)
        plugin = FEATURE_ID.search(metadata)
        if plugin and plugin.group(1) != "not-applicable":
            plugin_id = plugin.group(1)
            if plugin_id in feature_ids:
                fail(
                    errors,
                    path,
                    f"duplicate plugin-id {plugin_id!r}; first declared by "
                    f"{feature_ids[plugin_id].relative_to(ROOT)}",
                )
            feature_ids[plugin_id] = path
            relative = path.relative_to(DOCS).as_posix()
            if relative not in nav_text:
                fail(
                    errors, path, "feature guide is not included in zensical navigation"
                )

    manifest_ids = set(PLUGIN_ID.findall(MANIFEST.read_text()))
    missing = sorted(manifest_ids - set(feature_ids))
    extra = sorted(set(feature_ids) - manifest_ids)
    for plugin_id in missing:
        errors.append(
            f"distributions/default/manifest.yaml: selected plugin {plugin_id!r} "
            "has no feature guide"
        )
    for plugin_id in extra:
        path = feature_ids[plugin_id]
        fail(
            errors,
            path,
            f"feature guide plugin-id {plugin_id!r} is not selected by the default distribution",
        )

    for path in EXAMPLES.rglob("*.py"):
        try:
            ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            fail(errors, path, f"Python example does not parse: {exc.msg}")
    for path in EXAMPLES.rglob("*.yaml"):
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            fail(errors, path, f"YAML example does not parse: {exc}")

    provider_ids = source_provider_ids()
    auth_paths = authentication_document_paths()
    validate_navigation(errors)
    validate_yaml_snippets(
        errors,
        auth_paths,
        source_manifest_fields(),
        provider_ids,
        source_provider_config_fields(),
    )
    validate_source_references(
        errors,
        auth_paths,
        provider_ids,
        source_environment_names(),
        source_gateway_routes(),
    )
    validate_links(errors, auth_paths)

    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        print("\n".join(f"  - {error}" for error in errors), file=sys.stderr)
        return 1
    print(
        "Documentation validation passed "
        f"({len(markdown_files)} pages, {len(feature_ids)} feature guides, "
        f"{len(auth_paths)} authentication documents)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
