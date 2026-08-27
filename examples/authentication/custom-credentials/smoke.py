#!/usr/bin/env python3
"""HTTP smoke for the development-only custom credential topology."""

from __future__ import annotations

import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

FIXTURE_PROVIDER = "example.auth.fixture"
LOCAL_PROVIDER = "atlas.auth.local"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


class Browser:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def csrf(self) -> str:
        return next(
            cookie.value for cookie in self.cookies if cookie.name == "csrftoken"
        )

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        expected: int = 200,
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if data is not None:
            body = json.dumps(data).encode()
            headers.update({
                "Content-Type": "application/json",
                "Origin": self.base_url,
                "X-CSRFToken": self.csrf(),
            })
        request = urllib.request.Request(
            f"{self.base_url}{path}", body, headers, method=method
        )
        try:
            response = self.opener.open(request)
        except urllib.error.HTTPError as error:
            response = error
        payload = response.read()
        if response.status != expected:
            raise AssertionError(
                f"{method} {path}: expected {expected}, got {response.status}: "
                f"{payload[:500]!r}"
            )
        return json.loads(payload) if payload else {}

    def config(self) -> dict[str, Any]:
        return self.request("/auth/browser/v1/config")

    def login(
        self,
        provider: str,
        username: str,
        password: str,
        *,
        expected: int = 200,
    ) -> dict[str, Any]:
        return self.request(
            f"/auth/browser/v1/providers/{provider}/credentials",
            method="POST",
            data={"username": username, "password": password},
            expected=expected,
        )

    def logout(self) -> None:
        self.request(
            "/auth/browser/v1/session", method="DELETE", data={}, expected=204
        )


def compose(env_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def atlas_state(env_file: Path, username: str) -> dict[str, Any]:
    code = f"""
import json
from django.contrib.auth import get_user_model
from server.apps.catalog.models import ExternalIdentityLink, GroupMembershipGrant
users = get_user_model().objects.filter(username={username!r})
if not users.exists():
    print(json.dumps({{'principalCount': 0, 'linkCount': 0, 'actorCount': 0, 'groups': [], 'finiteExpiry': False}}))
else:
    user = users.get()
    actor = getattr(user, 'catalog_actor', None)
    grants = GroupMembershipGrant.objects.filter(actor_id=getattr(actor, 'entity_id', None), source_kind='provider', revoked_at__isnull=True)
    print(json.dumps({{
        'principalCount': users.count(),
        'linkCount': ExternalIdentityLink.objects.filter(user=user).count(),
        'actorCount': int(actor is not None),
        'groups': sorted(grants.values_list('group__entity__name', flat=True)),
        'finiteExpiry': bool(grants.exists() and all(item.expires_at is not None for item in grants)),
    }}))
"""
    result = compose(
        env_file,
        "exec",
        "-T",
        "backend",
        "python",
        "manage.py",
        "shell",
        "-c",
        code,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def main() -> None:
    env_file = Path(sys.argv[1] if len(sys.argv) > 1 else ".env")
    env = load_env(env_file)
    base_url = os.environ.get(
        "ATLAS_BASE_URL", f"http://localhost:{env.get('ATLAS_PORT', '18080')}"
    )
    fixture_password = env["ATLAS_FIXTURE_PASSWORD"]

    probe = Browser(base_url)
    config = probe.config()
    assert [item["id"] for item in config["providers"]] == [
        FIXTURE_PROVIDER,
        LOCAL_PROVIDER,
    ]

    empty = probe.login(FIXTURE_PROVIDER, "fixture-alice", "", expected=400)
    known = probe.login(FIXTURE_PROVIDER, "fixture-alice", "wrong", expected=400)
    unknown = probe.login(FIXTURE_PROVIDER, "does-not-exist", "wrong", expected=400)
    assert (
        known["error"]["category"]
        == unknown["error"]["category"]
        == "invalid_credentials"
    )
    assert fixture_password not in json.dumps((empty, known, unknown))

    outage = probe.login(
        FIXTURE_PROVIDER,
        "fixture-provider-outage",
        fixture_password,
        expected=503,
    )
    assert outage["error"]["category"] == "provider_unavailable"

    fallback = Browser(base_url)
    fallback.config()
    fallback.login(
        LOCAL_PROVIDER,
        env["ATLAS_LOCAL_FALLBACK_USERNAME"],
        env["ATLAS_LOCAL_FALLBACK_PASSWORD"],
    )
    fallback.logout()

    alice = Browser(base_url)
    alice.config()
    alice.login(FIXTURE_PROVIDER, "fixture-alice", fixture_password)
    state = atlas_state(env_file, "fixture-alice")
    assert state == {
        "principalCount": 1,
        "linkCount": 1,
        "actorCount": 1,
        "groups": ["custom-platform"],
        "finiteExpiry": True,
    }
    alice.request(
        "/api/systems/",
        method="POST",
        data={
            "metadata": {"name": f"custom-smoke-{uuid.uuid4().hex[:8]}"},
            "spec": {"owner": "group:custom-platform"},
        },
        expected=201,
    )
    alice.logout()

    repeated = Browser(base_url)
    repeated.config()
    repeated.login(FIXTURE_PROVIDER, "fixture-alice", fixture_password)
    assert atlas_state(env_file, "fixture-alice") == state
    repeated.logout()

    empty_groups = Browser(base_url)
    empty_groups.config()
    empty_groups.login(FIXTURE_PROVIDER, "fixture-empty", fixture_password)
    empty_state = atlas_state(env_file, "fixture-empty")
    assert empty_state["groups"] == []
    empty_groups.request(
        "/api/systems/",
        method="POST",
        data={
            "metadata": {"name": f"custom-denied-{uuid.uuid4().hex[:8]}"},
            "spec": {"owner": "group:custom-platform"},
        },
        expected=403,
    )
    empty_groups.logout()

    unavailable_groups = Browser(base_url)
    unavailable_groups.config()
    failure = unavailable_groups.login(
        FIXTURE_PROVIDER,
        "fixture-groups-unavailable",
        fixture_password,
        expected=403,
    )
    assert failure["error"]["category"] == "provisioning_failed"
    assert atlas_state(env_file, "fixture-groups-unavailable")["principalCount"] == 0

    logs = compose(env_file, "logs", "--no-color", "backend").stdout
    assert fixture_password not in logs
    assert env["ATLAS_LOCAL_FALLBACK_PASSWORD"] not in logs
    print("Custom credential authentication smoke test passed.")


if __name__ == "__main__":
    main()
