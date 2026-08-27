"""Create the operator-managed Group used for the denied-write check."""

from atlas_plugin_api import KIND_GROUP, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import GroupDetails

Entity = get_catalog_entity_model()
entity, _ = Entity.objects.get_or_create(kind=KIND_GROUP, name="gitea-operators")
GroupDetails.objects.update_or_create(entity=entity, defaults={"type": "team"})
