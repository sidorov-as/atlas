"""Minimal Meilisearch HTTP client.

Talks only to the configured endpoint: no proxies from the environment, no
redirects. The access key goes in a header and nowhere else; it is never part
of a message, a log line or `repr`.
"""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset({"succeeded", "failed", "canceled"})
_POLL_START_SECONDS = 0.05
_POLL_MAX_SECONDS = 1.0


class MeilisearchError(Exception):
    """The engine could not apply or answer a request."""


class MeilisearchApiError(MeilisearchError):
    def __init__(self, status: int, code: str | None, message: str) -> None:
        super().__init__(f"Meilisearch returned {status} ({code}): {message}")
        self.status = status
        self.code = code


class MeilisearchTaskError(MeilisearchError):
    def __init__(self, task_uid: int, status: str, code: str | None, message: str):
        super().__init__(f"Meilisearch task {task_uid} {status} ({code}): {message}")
        self.task_uid = task_uid
        self.code = code


class MeilisearchTimeoutError(MeilisearchError):
    pass


class MeilisearchClient:
    def __init__(
        self,
        url: str,
        key: str | None,
        *,
        request_timeout: float,
        task_timeout: float,
    ) -> None:
        self._url = url.rstrip("/")
        self._request_timeout = request_timeout
        self._task_timeout = task_timeout
        self._session = requests.Session()
        self._session.trust_env = False
        if key:
            self._session.headers["Authorization"] = f"Bearer {key}"

    def __repr__(self) -> str:
        return f"MeilisearchClient(url={self._url!r})"

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        timeout: float | None = None,
    ) -> Any:
        try:
            response = self._session.request(
                method,
                f"{self._url}{path}",
                json=json,
                timeout=timeout or self._request_timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise MeilisearchError(
                f"Meilisearch is unreachable at {self._url}: {type(exc).__name__}"
            ) from exc
        if response.status_code >= 400:
            code, message = None, response.reason or ""
            try:
                body = response.json()
                code, message = body.get("code"), body.get("message", message)
            except ValueError:
                pass
            if response.status_code in (401, 403):
                message = (
                    "the access key was rejected or is missing; check the "
                    "plugin's 'key' setting"
                )
            raise MeilisearchApiError(response.status_code, code, message)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def run_task(self, method: str, path: str, *, json: Any = None) -> dict[str, Any]:
        """Send a write and wait until the engine has finished applying it."""
        enqueued = self.request(method, path, json=json)
        return self.wait_for_task(enqueued["taskUid"])

    def wait_for_task(self, task_uid: int) -> dict[str, Any]:
        deadline = time.monotonic() + self._task_timeout
        delay = _POLL_START_SECONDS
        while True:
            task = self.request("GET", f"/tasks/{task_uid}")
            status = task["status"]
            if status == "succeeded":
                return task
            if status in TERMINAL_STATUSES:
                error = task.get("error") or {}
                raise MeilisearchTaskError(
                    task_uid, status, error.get("code"), error.get("message", "")
                )
            if time.monotonic() + delay > deadline:
                raise MeilisearchTimeoutError(
                    f"Meilisearch task {task_uid} did not finish within "
                    f"{self._task_timeout:g}s (status {status})"
                )
            time.sleep(delay)
            delay = min(delay * 2, _POLL_MAX_SECONDS)
