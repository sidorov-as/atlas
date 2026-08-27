#!/usr/bin/env python3
"""Drive the disposable Gitea OAuth flow and assert Atlas behavior."""

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

PROVIDER_ID = "atlas.auth.gitea"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if tag == "form":
            self._current = {
                "action": html.unescape(values.get("action") or ""),
                "inputs": {},
            }
            self.forms.append(self._current)
        elif tag == "input" and self._current is not None:
            name = values.get("name")
            if name:
                self._current["inputs"][name] = html.unescape(
                    values.get("value") or ""
                )

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._current = None


def forms(document: bytes) -> list[dict[str, Any]]:
    parser = FormParser()
    parser.feed(document.decode(errors="replace"))
    return parser.forms


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
        parsed_url = urllib.parse.urlsplit(url)
        if parsed_url.hostname == "gitea.localhost":
            # Browsers reserve *.localhost for loopback. Python's system DNS
            # resolver does not consistently implement that rule on macOS,
            # so the smoke transport connects to the published loopback port.
            url = urllib.parse.urlunsplit(
                parsed_url._replace(
                    netloc=f"localhost:{parsed_url.port or 80}"
                )
            )
        headers: dict[str, str] = {"Accept": "text/html,application/json"}
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
        call = urllib.request.Request(
            url, data=body, headers=headers, method=method
        )
        try:
            response = self.opener.open(call)
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
        assert [item["id"] for item in config["providers"]] == [PROVIDER_ID]
        assert config["providers"][0]["flowKind"] == "redirect"

        challenge = json.loads(
            self.request(
                f"{self.base_url}/auth/browser/v1/providers/{PROVIDER_ID}/start",
                method="POST",
                data={"returnUrl": "/"},
                authenticated_write=True,
            )
        )
        login_page = self.request(challenge["redirectUrl"])
        login_form = next(
            item for item in forms(login_page) if "user_name" in item["inputs"]
        )
        login_values = dict(login_form["inputs"])
        login_values.update({"user_name": username, "password": password})
        result = self.request(
            urllib.parse.urljoin(challenge["redirectUrl"], login_form["action"]),
            method="POST",
            data=login_values,
            form=True,
            expected=(200, 404),
        )

        consent_forms = [
            item
            for item in forms(result)
            if "client_id" in item["inputs"]
            and "oauth" in item["action"]
        ]
        if consent_forms:
            consent = consent_forms[0]
            consent_values = dict(consent["inputs"])
            consent_values["granted"] = "true"
            self.request(
                urllib.parse.urljoin(
                    challenge["redirectUrl"], consent["action"]
                ),
                method="POST",
                data=consent_values,
                form=True,
                expected=(200, 404),
            )

        session = json.loads(
            self.request(f"{self.base_url}/auth/browser/v1/session")
        )
        assert session["meta"]["is_authenticated"] is True
        assert session["data"]["user"]["username"] == username


def atlas_state(env_file: Path, username: str) -> dict[str, Any]:
    code = f"""
import json
from django.contrib.auth import get_user_model
from server.apps.catalog.models import ExternalIdentityLink, GroupMembershipGrant
user = get_user_model().objects.get(username={username!r})
print(json.dumps({{
    'principalCount': get_user_model().objects.filter(username={username!r}).count(),
    'linkCount': ExternalIdentityLink.objects.filter(user=user).count(),
    'subject': ExternalIdentityLink.objects.get(user=user).external_subject,
    'providerGrants': GroupMembershipGrant.objects.filter(
        actor_id=user.catalog_actor.entity_id,
        source_kind='provider',
        revoked_at__isnull=True,
    ).count(),
    'isStaff': user.is_staff,
    'isSuperuser': user.is_superuser,
}}))
"""
    runtime_command = (
        ". /run/atlas-auth/gitea.env; "
        "export GITEA_CLIENT_ID GITEA_CLIENT_SECRET; "
        'exec python manage.py shell -c "$1"'
    )
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "exec",
            "-T",
            "backend",
            "/bin/sh",
            "-ec",
            runtime_command,
            "atlas-state",
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
    username = env["ATLAS_GITEA_TEST_USERNAME"]
    password = env["ATLAS_GITEA_TEST_PASSWORD"]
    run_id = uuid.uuid4().hex[:8]

    first = Browser(atlas_url)
    first.login(username, password)
    state = atlas_state(env_file, username)
    assert state["principalCount"] == 1
    assert state["linkCount"] == 1
    assert state["subject"].isdigit()
    assert state["providerGrants"] == 0
    assert state["isStaff"] is False
    assert state["isSuperuser"] is False

    first.request(f"{atlas_url}/api/systems/")
    first.request(
        f"{atlas_url}/api/systems/",
        method="POST",
        data={
            "metadata": {"name": f"gitea-scope-cannot-grant-{run_id}"},
            "spec": {"owner": "group:gitea-operators"},
        },
        authenticated_write=True,
        expected=403,
    )

    second = Browser(atlas_url)
    second.login(username, password)
    assert atlas_state(env_file, username) == state
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

    print("Gitea OAuth2 browser smoke test passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Gitea OAuth2 browser smoke failed: {error}", file=sys.stderr)
        raise
