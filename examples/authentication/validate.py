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


CHECKS = {
    "syntax": validate_syntax,
    "schemas": validate_schemas,
    "compose": validate_compose,
    "docs": validate_docs_commands,
    "imports": validate_import_boundaries,
    "secrets": validate_secrets,
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
