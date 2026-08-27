"""Git host connector interface — the `atlas.ingestion.connectors.v1`
extension point contract.

`GitConnector` (`connectors/git.py`) is the provider-agnostic v1
implementation, registered once per configured `sources[]` entry rather than
hard-coded to one host. The pipeline talks to this interface, resolved from
`atlas_plugin_ingestion.extension_points.connectors`, rather than a git-host
API directly, so a source-specific connector can be added later without
touching discovery, parsing, or upsert.
"""

from abc import ABC, abstractmethod

from atlas_plugin_ingestion.models import RegisteredRepository

MANIFEST_FILENAME = "catalog-info.yaml"


class SourceConnector(ABC):
    @abstractmethod
    def list_manifest_paths(self, repo: RegisteredRepository) -> list[str]:
        """Every `**/catalog-info.yaml` path in `repo`'s default branch."""

    @abstractmethod
    def list_paths(self, repo: RegisteredRepository) -> list[str]:
        """Every file path in `repo`'s default branch, not just manifests —
        used to resolve `Include` glob patterns (ingestion-manifest-includes
        spec's "Include paths support glob patterns")."""

    @abstractmethod
    def fetch_file(self, repo: RegisteredRepository, path: str, ref: str) -> bytes:
        """Raw bytes of `path` at commit `ref`."""

    @abstractmethod
    def get_head_sha(self, repo: RegisteredRepository) -> str:
        """The commit SHA at the tip of `repo`'s default branch."""
