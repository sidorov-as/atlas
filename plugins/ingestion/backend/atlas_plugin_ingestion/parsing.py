"""Multi-document `catalog-info.yaml` parsing — the `atlas.ingestion.parsers.v1` extension point contract.

`max_nesting_depth` bounds how deeply a fetched document's YAML may nest
(fetched content is bounded before parsing, including unbounded YAML parsing),
enforced via a `SafeLoader` subclass that counts `compose_node` recursion
rather than a post-hoc walk of the already-constructed Python object, so a
pathological document is rejected during composition instead of after it has
already been fully built in memory.
"""

from abc import ABC, abstractmethod
from typing import Any

import yaml

from .limits import DEFAULT_MAX_YAML_NESTING_DEPTH


class YamlDocumentTooComplexError(Exception):
    """Raised when a fetched document's YAML nesting depth exceeds the
    configured maximum (excessively nested YAML is
    rejected)."""


class DocumentParser(ABC):
    @abstractmethod
    def parse(
        self,
        content: bytes,
        *,
        max_nesting_depth: int = DEFAULT_MAX_YAML_NESTING_DEPTH,
    ) -> list[dict[str, Any]]:
        """Split a fetched manifest Artifact into raw document dicts."""


def _depth_limited_loader(max_depth: int) -> type[yaml.SafeLoader]:
    """A fresh `yaml.SafeLoader` subclass (one per call, so concurrent
    parses never share mutable depth state) that raises
    `YamlDocumentTooComplexError` once node composition nests deeper than
    `max_depth`."""

    class _DepthLimitedSafeLoader(yaml.SafeLoader):
        _depth = 0

        def compose_node(self, parent: Any, index: Any) -> Any:
            self._depth += 1
            if self._depth > max_depth:
                raise YamlDocumentTooComplexError(
                    f"YAML document nesting exceeds the configured maximum "
                    f"depth of {max_depth}",
                )
            try:
                return super().compose_node(parent, index)
            finally:
                self._depth -= 1

    return _DepthLimitedSafeLoader


def parse_manifest(
    content: bytes,
    *,
    max_nesting_depth: int = DEFAULT_MAX_YAML_NESTING_DEPTH,
) -> list[dict[str, Any]]:
    """Split a `---`-separated manifest file into raw document dicts.

    Empty documents (a leading/trailing `---`, or a blank document between
    two separators) are dropped rather than passed on as `None`.
    """
    loader = _depth_limited_loader(max_nesting_depth)
    documents = yaml.load_all(content.decode("utf-8"), Loader=loader)
    return [document for document in documents if document]


class CatalogInfoYamlParser(DocumentParser):
    """`DocumentParser` implementation for `catalog-info.yaml` manifests."""

    def parse(
        self,
        content: bytes,
        *,
        max_nesting_depth: int = DEFAULT_MAX_YAML_NESTING_DEPTH,
    ) -> list[dict[str, Any]]:
        return parse_manifest(content, max_nesting_depth=max_nesting_depth)


PARSER_ID = "catalog-info-yaml"
"""Registration key against `atlas.ingestion.parsers.v1`."""
