import pytest
from atlas_plugin_api.search_conformance import SearchEngineConformance


class TestMeilisearchEngineConformance(SearchEngineConformance):
    @pytest.fixture(autouse=True)
    def _instance(self, real_engine):
        self._engine = real_engine

    def make_engine(self):
        return self._engine
