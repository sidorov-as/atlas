#!/usr/bin/env python3
"""Idempotently create Gitea's disposable OAuth app and runtime secret file."""

from __future__ import annotations

import os
import pwd
import shlex
from pathlib import Path

from gitea_api import request

APP_NAME = "atlas-ingestion-example"
CALLBACK = "http://localhost:18090/auth/browser/v1/providers/atlas.auth.gitea/callback"


def main() -> None:
    secret_file = Path("/run/atlas-ingestion/gitea.env")
    applications = request("/api/v1/user/applications/oauth2") or []
    matching = [item for item in applications if item.get("name") == APP_NAME]

    if matching and secret_file.exists():
        print("Gitea OAuth application and runtime secret already exist.")
        return

    for application in matching:
        request(
            f"/api/v1/user/applications/oauth2/{application['id']}",
            method="DELETE",
        )

    application = request(
        "/api/v1/user/applications/oauth2",
        method="POST",
        data={
            "name": APP_NAME,
            "redirect_uris": [CALLBACK],
            "confidential_client": True,
        },
    )
    client_id = application.get("client_id")
    client_secret = application.get("client_secret")
    if not client_id or not client_secret:
        raise RuntimeError("Gitea did not return OAuth client credentials")

    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(
        f"export GITEA_CLIENT_ID={shlex.quote(client_id)}\n"
        f"export GITEA_CLIENT_SECRET={shlex.quote(client_secret)}\n",
    )
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
    print("Created disposable Gitea OAuth application.")


if __name__ == "__main__":
    main()
