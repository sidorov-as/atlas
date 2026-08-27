from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.db import models


class SystemDetails(models.Model):
    """Kind-specific data for a `CatalogEntity` of kind `system`.

    A System has no fields of its own beyond the common `CatalogEntity`
    envelope — `owner` lives there too. This row still exists (empty) so a
    System is a details-backed entity like every other kind.
    """

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="system_details",
    )

    class Meta:
        app_label = "catalog"

    def __str__(self) -> str:
        return self.entity.name
