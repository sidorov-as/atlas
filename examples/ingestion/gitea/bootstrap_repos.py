#!/usr/bin/env python3
"""Idempotently provision the disposable Gitea org/repos/token this example's
ingestion source reads from: creates one ingestion access token, one
organization, and one repository per curated fixture under `/fixtures`,
pushing (or updating) each fixture's content into that repository.

Most fixtures are a single `<name>.yaml` file, pushed as the repository's
`catalog-info.yaml`. A fixture may instead be a directory (currently
`booking-reservations`, to demonstrate `kind: Include` manifest composition)
containing its own `catalog-info.yaml` plus any fragment files it includes;
every file in that directory is pushed at its path relative to the
directory, preserving the repository layout the `Include` paths expect.

Uses Gitea's REST "contents" API to write files directly rather than a real
git push, so this container needs no git tooling of its own.
"""

from __future__ import annotations

import base64
import os
import pwd
import shlex
from pathlib import Path

from gitea_api import request

TOKEN_NAME = "atlas-ingestion-example"
ORG_NAME = "atlas-demo"
FIXTURES_DIR = Path("/fixtures")
REPOSITORIES = ("search-discovery", "payments-payouts", "booking-reservations")
MANIFEST_PATH = "catalog-info.yaml"
DEFAULT_BRANCH = "main"


def ensure_ingestion_token() -> str:
    secret_file = Path("/run/atlas-ingestion/ingestion.env")
    admin_username = _admin_username()
    existing = request(f"/api/v1/users/{admin_username}/tokens") or []
    matching = [item for item in existing if item.get("name") == TOKEN_NAME]

    if matching and secret_file.exists():
        print("Gitea ingestion token already exists.")
        return secret_file.read_text()

    for token in matching:
        request(
            f"/api/v1/users/{admin_username}/tokens/{token['id']}",
            method="DELETE",
        )

    created = request(
        f"/api/v1/users/{admin_username}/tokens",
        method="POST",
        data={
            "name": TOKEN_NAME,
            "scopes": ["write:repository", "write:organization", "read:user"],
        },
    )
    token_value = created.get("sha1")
    if not token_value:
        raise RuntimeError("Gitea did not return an access token value")

    secret_file.parent.mkdir(parents=True, exist_ok=True)
    contents = f"export GITEA_INGESTION_TOKEN={shlex.quote(token_value)}\n"
    secret_file.write_text(contents)
    secret_file.chmod(0o600)
    # `/run/atlas-ingestion` is a fresh named volume mount, created root-owned
    # before any container touches it, so this script must run as root to
    # create the file at all (`backend`/
    # `initializer` run as non-root `appuser`, which can only read this file
    # afterwards — not write into the root-owned directory). Owning the file
    # itself by `appuser` keeps the 0o600 mode meaningful for that reader
    # instead of leaving it root-owned and unreadable to everyone else.
    appuser = pwd.getpwnam("appuser")
    os.chown(secret_file, appuser.pw_uid, appuser.pw_gid)
    print("Created disposable Gitea ingestion access token.")
    return contents


def _admin_username() -> str:
    return os.environ["GITEA_ADMIN_USERNAME"]


def ensure_org() -> None:
    try:
        request(f"/api/v1/orgs/{ORG_NAME}")
        print(f"Gitea organization {ORG_NAME!r} already exists.")
        return
    except RuntimeError as error:
        if "404" not in str(error):
            raise
    request(
        "/api/v1/orgs",
        method="POST",
        data={"username": ORG_NAME, "visibility": "public"},
    )
    print(f"Created Gitea organization {ORG_NAME!r}.")


def ensure_repository(name: str) -> None:
    try:
        request(f"/api/v1/repos/{ORG_NAME}/{name}")
        print(f"Gitea repository {ORG_NAME}/{name} already exists.")
        return
    except RuntimeError as error:
        if "404" not in str(error):
            raise
    request(
        f"/api/v1/orgs/{ORG_NAME}/repos",
        method="POST",
        data={
            "name": name,
            "auto_init": True,
            "default_branch": DEFAULT_BRANCH,
            "private": False,
        },
    )
    print(f"Created Gitea repository {ORG_NAME}/{name}.")


def push_file(repo: str, repo_path: str, content: bytes) -> None:
    encoded = base64.b64encode(content).decode()
    existing_sha = None
    try:
        existing = request(
            f"/api/v1/repos/{ORG_NAME}/{repo}/contents/{repo_path}"
            f"?ref={DEFAULT_BRANCH}",
        )
        existing_sha = existing.get("sha")
    except RuntimeError as error:
        if "404" not in str(error):
            raise

    payload = {
        "content": encoded,
        "branch": DEFAULT_BRANCH,
        "message": f"Set {repo_path} from the atlas ingestion example fixture",
    }
    if existing_sha is None:
        request(
            f"/api/v1/repos/{ORG_NAME}/{repo}/contents/{repo_path}",
            method="POST",
            data=payload,
        )
        print(f"Created {repo_path} in {ORG_NAME}/{repo}.")
    else:
        payload["sha"] = existing_sha
        request(
            f"/api/v1/repos/{ORG_NAME}/{repo}/contents/{repo_path}",
            method="PUT",
            data=payload,
        )
        print(f"Updated {repo_path} in {ORG_NAME}/{repo}.")


def push_manifest(name: str) -> None:
    """Single-file fixture: `/fixtures/<name>.yaml` becomes the repository's
    `catalog-info.yaml`."""
    content = (FIXTURES_DIR / f"{name}.yaml").read_bytes()
    push_file(name, MANIFEST_PATH, content)


def push_fixture_tree(name: str) -> None:
    """Directory fixture: every file under `/fixtures/<name>/` is pushed at
    its path relative to that directory, so an `Include` document's
    `spec.paths` (resolved relative to the file that declares them) still
    match once the tree lands in the repository."""
    root = FIXTURES_DIR / name
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        repo_path = file_path.relative_to(root).as_posix()
        push_file(name, repo_path, file_path.read_bytes())


def main() -> None:
    ensure_ingestion_token()
    ensure_org()
    for name in REPOSITORIES:
        ensure_repository(name)
        if (FIXTURES_DIR / name).is_dir():
            push_fixture_tree(name)
        else:
            push_manifest(name)


if __name__ == "__main__":
    main()
