import logging

import pytest
import requests

from atlas_plugin_search_meilisearch import client as client_module
from atlas_plugin_search_meilisearch.client import (
    MeilisearchApiError,
    MeilisearchClient,
    MeilisearchError,
    MeilisearchTaskError,
    MeilisearchTimeoutError,
)


class FakeResponse:
    def __init__(self, status=200, body=None, reason="OK"):
        self.status_code = status
        self._body = body
        self.reason = reason
        self.content = b"x" if body is not None else b""

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


def _client(responses, *, task_timeout=5.0, key="s3cret"):
    client = MeilisearchClient(
        "http://meili:7700/", key, request_timeout=2, task_timeout=task_timeout
    )
    sent = []
    queue = list(responses)

    def request(method, url, **kwargs):
        sent.append((method, url, kwargs))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client._session.request = request
    client.sent = sent
    return client


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(client_module.time, "sleep", lambda s: None)


def test_requests_use_only_the_configured_target_without_proxies_or_redirects():
    client = _client([FakeResponse(200, {"status": "available"})])
    client.request("GET", "/health")

    (_, url, kwargs) = client.sent[0]
    assert url == "http://meili:7700/health"
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == 2
    assert client._session.trust_env is False


def test_the_key_is_sent_as_a_header_and_never_shown(caplog):
    client = _client([])
    assert client._session.headers["Authorization"] == "Bearer s3cret"
    assert "s3cret" not in repr(client)


def test_no_key_means_no_authorization_header():
    assert "Authorization" not in _client([], key=None)._session.headers


def test_unreachable_instance_raises_without_the_key():
    client = _client([requests.ConnectionError("boom s3cret")])
    with pytest.raises(MeilisearchError) as raised:
        client.request("GET", "/health")
    assert "unreachable" in str(raised.value)
    assert "s3cret" not in str(raised.value)


def test_a_rejected_key_names_the_setting_not_the_value():
    client = _client([FakeResponse(401, {"code": "invalid_api_key", "message": "x"})])
    with pytest.raises(MeilisearchApiError) as raised:
        client.request("GET", "/indexes")
    assert "'key'" in str(raised.value)
    assert "s3cret" not in str(raised.value)


def test_api_errors_carry_the_engine_code():
    client = _client([FakeResponse(404, {"code": "index_not_found", "message": "m"})])
    with pytest.raises(MeilisearchApiError) as raised:
        client.request("GET", "/indexes/x")
    assert raised.value.code == "index_not_found"


def test_run_task_waits_until_the_task_succeeds():
    client = _client(
        [
            FakeResponse(202, {"taskUid": 4}),
            FakeResponse(200, {"status": "enqueued"}),
            FakeResponse(200, {"status": "processing"}),
            FakeResponse(200, {"status": "succeeded"}),
        ]
    )
    assert client.run_task("POST", "/indexes", json={})["status"] == "succeeded"
    assert [u for _, u, _ in client.sent][1:] == ["http://meili:7700/tasks/4"] * 3


def test_a_task_the_engine_marks_failed_is_an_error():
    client = _client(
        [
            FakeResponse(202, {"taskUid": 4}),
            FakeResponse(
                200,
                {"status": "failed", "error": {"code": "bad", "message": "no"}},
            ),
        ]
    )
    with pytest.raises(MeilisearchTaskError) as raised:
        client.run_task("POST", "/indexes", json={})
    assert raised.value.code == "bad"


def test_a_task_that_does_not_finish_in_time_times_out(monkeypatch):
    clock = iter(range(0, 1000, 20))
    monkeypatch.setattr(client_module.time, "monotonic", lambda: next(clock))
    client = _client(
        [FakeResponse(202, {"taskUid": 4})]
        + [FakeResponse(200, {"status": "processing"})] * 10,
        task_timeout=30,
    )
    with pytest.raises(MeilisearchTimeoutError, match="30s"):
        client.run_task("POST", "/indexes", json={})


def test_nothing_logs_the_key(caplog):
    caplog.set_level(logging.DEBUG)
    client = _client([FakeResponse(200, {"ok": 1})])
    client.request("GET", "/health")
    assert "s3cret" not in caplog.text
