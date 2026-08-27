"""Architecture Relationship contract (`core-plugin-contract-surface` spec:
"Core publishes its plugin-facing surface as contract types").

Stands in for `server.apps.catalog.models.architecture_relationship` — a
declared, directed architecture interaction between catalog entities,
authored manually or by ingestion, never regenerated from entity
specifications (unlike `Relation`, see `relations.py`). Like `CatalogEntity`
(catalog.py's docstring), the concrete Django model can't move here, so this
publishes a `get_architecture_relationship_model()` runtime accessor plus the
`origin` values as plain constants, needing no import of the target class at
all.
"""

from django.apps import apps as _django_apps

ARCHITECTURE_RELATIONSHIP_LABEL = "catalog.ArchitectureRelationship"

ARCHITECTURE_RELATIONSHIP_ORIGIN_MANUAL = "manual"
ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML = "yaml"


def get_architecture_relationship_model() -> type:
    """Resolve Core's concrete `ArchitectureRelationship` model via Django's
    app registry, the same lazy-resolution mechanism
    `get_catalog_entity_model()` uses. Only callable after `django.setup()` —
    from inside a function body, never cached at plugin module import time.
    """
    return _django_apps.get_model(ARCHITECTURE_RELATIONSHIP_LABEL)
