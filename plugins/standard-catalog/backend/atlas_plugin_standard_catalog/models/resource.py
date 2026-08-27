from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.db import models


class ResourceDetails(models.Model):
    """Kind-specific data for a `CatalogEntity` of kind `resource`."""

    TYPE_CHOICES: ClassVar[list] = [
        ("database", "Database"),
        ("cache", "Cache"),
        ("bucket", "Bucket"),
        ("queue", "Queue"),
        ("cluster", "Cluster"),
    ]

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="resource_details",
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    system = models.ForeignKey(
        CATALOG_ENTITY_LABEL,
        on_delete=models.PROTECT,
        related_name="resources",
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "catalog"

    def __str__(self) -> str:
        return self.entity.name
