"""Fixtures for tests that need a real Meilisearch instance.

CI and `make ci` start one and export `ATLAS_TEST_MEILISEARCH_URL` (and
`ATLAS_TEST_MEILISEARCH_KEY` for an instance that enforces a key). Without the
URL these tests are skipped, so a plain `pytest` run needs no extra service;
set `ATLAS_REQUIRE_MEILISEARCH=1` to turn that skip into a failure.
"""

import os
import uuid

import pytest

from atlas_plugin_search_meilisearch.client import MeilisearchClient
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig
from atlas_plugin_search_meilisearch.engine import MeilisearchSearchEngine


@pytest.fixture
def meilisearch_config():
    url = os.environ.get("ATLAS_TEST_MEILISEARCH_URL")
    if not url:
        if os.environ.get("ATLAS_REQUIRE_MEILISEARCH"):
            pytest.fail("ATLAS_TEST_MEILISEARCH_URL is required but not set")
        pytest.skip("ATLAS_TEST_MEILISEARCH_URL is not set")
    return SearchMeilisearchPluginConfig(
        url=url,
        key=os.environ.get("ATLAS_TEST_MEILISEARCH_KEY") or None,
        index=f"atlas-test-{uuid.uuid4().hex[:12]}",
        taskTimeoutSeconds=30,
    )


@pytest.fixture
def real_engine(meilisearch_config):
    """An engine on a fresh, isolated index that is dropped afterwards."""
    engine = MeilisearchSearchEngine(meilisearch_config)
    yield engine
    client = MeilisearchClient(
        meilisearch_config.url,
        meilisearch_config.key,
        request_timeout=10,
        task_timeout=30,
    )
    client.request("DELETE", f"/indexes/{meilisearch_config.index}")
