import pytest
from atlas_plugin_api.search_conformance import SearchEngineConformance

from atlas_plugin_search_postgres.engine import PostgresSearchEngine


class TestPostgresEngineConformance(SearchEngineConformance):
    @pytest.fixture(autouse=True)
    def _database(self, db):
        """The adapter stores its index in the database."""

    def make_engine(self):
        return PostgresSearchEngine()
