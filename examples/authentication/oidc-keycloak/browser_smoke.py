#!/usr/bin/env python3
"""Drive the disposable Keycloak login as a browser and assert Atlas state."""

from __future__ import annotations

import html
import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

PROVIDER_ID = "atlas.auth.oidc"


class LoginFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if tag == "form" and values.get("id") == "kc-form-login":
            self.action = html.unescape(values.get("action") or "")


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
        url: str,
        *,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        form: bool = False,
        authenticated_write: bool = False,
        expected: int | tuple[int, ...] = 200,
    ) -> bytes:
        headers: dict[str, str] = {"Accept": "application/json"}
        body = None
        if data is not None:
            if form:
                body = urllib.parse.urlencode(data).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                body = json.dumps(data).encode()
                headers["Content-Type"] = "application/json"
        if authenticated_write:
            headers["Origin"] = self.base_url
            headers["X-CSRFToken"] = self.csrf()
        request = urllib.request.Request(
            url, data=body, headers=headers, method=method
        )
        try:
            response = self.opener.open(request)
        except urllib.error.HTTPError as error:
            response = error
        payload = response.read()
        expected_statuses = (expected,) if isinstance(expected, int) else expected
        if response.status not in expected_statuses:
            raise AssertionError(
                f"{method} {url}: expected {expected}, got {response.status}: "
                f"{payload[:500]!r}"
            )
        return payload

    def login(self, username: str, password: str) -> None:
        config = json.loads(
            self.request(f"{self.base_url}/auth/browser/v1/config")
        )
        providers = config["providers"]
        assert [provider["id"] for provider in providers] == [PROVIDER_ID]
        assert all(provider["flowKind"] != "credentials" for provider in providers)

        challenge = json.loads(
            self.request(
                f"{self.base_url}/auth/browser/v1/providers/{PROVIDER_ID}/start",
                method="POST",
                data={"returnUrl": "/"},
                authenticated_write=True,
            )
        )
        login_page = self.request(challenge["redirectUrl"]).decode()
        # Browsers treat loopback HTTP as a potentially trustworthy origin and
        # return Keycloak's Secure transient cookies. Python's CookieJar does
        # not implement that localhost exception, so mirror browser behavior
        # for this disposable HTTP-only fixture.
        for cookie in self.cookies:
            if cookie.domain == "localhost.local":
                cookie.secure = False
        parser = LoginFormParser()
        parser.feed(login_page)
        if not parser.action:
            raise AssertionError("Keycloak login form was not found")
        self.request(
            parser.action,
            method="POST",
            data={
                "username": username,
                "password": password,
                "credentialId": "",
            },
            form=True,
            # The callback succeeded before this final response. Vite returns
            # 404 for `/` when urllib retains `Accept: application/json`;
            # an interactive browser receives the SPA document instead.
            expected=(200, 404),
        )
        session = json.loads(
            self.request(f"{self.base_url}/auth/browser/v1/session")
        )
        assert session["meta"]["is_authenticated"] is True
        assert session["data"]["user"]["username"] == username


def json_request(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, str] | None = None,
    token: str | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def keycloak_membership(
    keycloak_url: str,
    env: dict[str, str],
) -> tuple[str, str, str]:
    token = json_request(
        f"{keycloak_url}/realms/master/protocol/openid-connect/token",
        method="POST",
        data={
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": env["KEYCLOAK_ADMIN"],
            "password": env["KEYCLOAK_ADMIN_PASSWORD"],
        },
    )["access_token"]
    users = json_request(
        f"{keycloak_url}/admin/realms/atlas-example/users?"
        + urllib.parse.urlencode(
            {"username": env["ATLAS_OIDC_TEST_USERNAME"], "exact": "true"}
        ),
        token=token,
    )
    groups = json_request(
        f"{keycloak_url}/admin/realms/atlas-example/groups?"
        + urllib.parse.urlencode({"search": "atlas-platform", "exact": "true"}),
        token=token,
    )
    assert len(users) == 1 and len(groups) == 1
    return token, users[0]["id"], groups[0]["id"]


def set_group(
    keycloak_url: str,
    *,
    token: str,
    user_id: str,
    group_id: str,
    present: bool,
) -> None:
    url = (
        f"{keycloak_url}/admin/realms/atlas-example/users/{user_id}/groups/"
        f"{group_id}"
    )
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="PUT" if present else "DELETE",
    )
    with urllib.request.urlopen(request) as response:
        assert response.status == 204


def atlas_state(env_file: Path, username: str) -> dict[str, Any]:
    code = f"""
import json
from django.contrib.auth import get_user_model
from server.apps.catalog.models import ExternalIdentityLink, GroupMembershipGrant
user = get_user_model().objects.get(username={username!r})
actor_id = user.catalog_actor.entity_id
grants = GroupMembershipGrant.objects.filter(
    actor_id=actor_id,
    source_kind='provider',
    revoked_at__isnull=True,
).values_list('group__entity__name', flat=True)
print(json.dumps({{
    'principalCount': get_user_model().objects.filter(username={username!r}).count(),
    'linkCount': ExternalIdentityLink.objects.filter(user=user).count(),
    'groups': sorted(grants),
}}))
"""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "exec",
            "-T",
            "backend",
            "python",
            "manage.py",
            "shell",
            "-c",
            code,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def main() -> None:
    env_file = Path(os.environ.get("ATLAS_COMPOSE_ENV_FILE", ".env"))
    if not env_file.exists():
        env_file = Path(".env.example")
    env = load_env(env_file)
    atlas_url = os.environ.get(
        "ATLAS_BASE_URL", f"http://localhost:{env.get('ATLAS_PORT', '18080')}"
    )
    keycloak_url = os.environ.get(
        "KEYCLOAK_BASE_URL",
        f"http://localhost:{env.get('KEYCLOAK_PORT', '18081')}",
    )
    username = env["ATLAS_OIDC_TEST_USERNAME"]
    password = env["ATLAS_OIDC_TEST_PASSWORD"]
    run_id = uuid.uuid4().hex[:8]

    first = Browser(atlas_url)
    first.login(username, password)
    first.request(
        f"{atlas_url}/api/systems/",
        method="POST",
        data={
            "metadata": {"name": f"oidc-smoke-allowed-{run_id}"},
            "spec": {"owner": "group:oidc-platform"},
        },
        authenticated_write=True,
        expected=201,
    )
    assert atlas_state(env_file, username) == {
        "principalCount": 1,
        "linkCount": 1,
        "groups": ["oidc-platform"],
    }

    token, user_id, group_id = keycloak_membership(keycloak_url, env)
    set_group(
        keycloak_url,
        token=token,
        user_id=user_id,
        group_id=group_id,
        present=False,
    )
    try:
        second = Browser(atlas_url)
        second.login(username, password)
        assert atlas_state(env_file, username) == {
            "principalCount": 1,
            "linkCount": 1,
            "groups": [],
        }
        second.request(
            f"{atlas_url}/api/systems/",
            method="POST",
            data={
                "metadata": {"name": f"oidc-smoke-denied-{run_id}"},
                "spec": {"owner": "group:oidc-platform"},
            },
            authenticated_write=True,
            expected=403,
        )
        second.request(
            f"{atlas_url}/auth/browser/v1/session",
            method="DELETE",
            authenticated_write=True,
            expected=204,
        )
        session = json.loads(
            second.request(f"{atlas_url}/auth/browser/v1/session")
        )
        assert session["meta"]["is_authenticated"] is False
    finally:
        set_group(
            keycloak_url,
            token=token,
            user_id=user_id,
            group_id=group_id,
            present=True,
        )

    print("Keycloak OIDC browser smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"OIDC browser smoke failed: {error}", file=sys.stderr)
        raise
