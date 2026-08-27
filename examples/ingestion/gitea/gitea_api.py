#!/usr/bin/env python3
"""Shared HTTP helper for talking to the disposable Gitea instance's admin
API, used by both `bootstrap_oauth.py` (login) and `bootstrap_repos.py`
(ingestion fixtures)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any


def request(path: str, *, method: str = 'GET', data: Any = None) -> Any:
    origin = os.environ['GITEA_INTERNAL_ORIGIN'].rstrip('/')
    credentials = (
        f"{os.environ['GITEA_ADMIN_USERNAME']}:"
        f"{os.environ['GITEA_ADMIN_PASSWORD']}"
    )
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '
        + base64.b64encode(credentials.encode()).decode(),
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json'
    call = urllib.request.Request(
        f'{origin}{path}', data=body, headers=headers, method=method,
    )
    try:
        with urllib.request.urlopen(call) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors='replace')[:500]
        raise RuntimeError(
            f'Gitea bootstrap {method} {path} failed with {error.code}: {detail}',
        ) from error
    return json.loads(payload) if payload else None
