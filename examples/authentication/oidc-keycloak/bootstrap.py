"""Idempotently create the Atlas-side targets for the disposable realm."""

from atlas_plugin_api import KIND_GROUP, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import GroupDetails

Entity = get_catalog_entity_model()

for name in ("oidc-platform", "oidc-readers"):
    entity, _ = Entity.objects.get_or_create(kind=KIND_GROUP, name=name)
    GroupDetails.objects.update_or_create(
        entity=entity,
        defaults={"type": "team"},
    )
