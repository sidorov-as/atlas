from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.db import models


class ComponentDetails(models.Model):
    """Kind-specific data for a `CatalogEntity` of kind `component`.

    `system`/`provides_apis`/`consumes_apis`/`depends_on` are FK/M2M to
    `CatalogEntity` directly — the DB can't constrain them to the right kind
    (`system` to `system`-kind rows, `provides_apis`/`consumes_apis` to
    `api`-kind rows, `depends_on` to `resource`-kind rows), so callers must
    resolve those refs with the matching `expected_kind`.
    """

    TYPE_CHOICES: ClassVar[list] = [
        ("service", "Service"),
        ("website", "Website"),
        ("library", "Library"),
        ("worker", "Worker"),
    ]
    LIFECYCLE_CHOICES: ClassVar[list] = [
        ("experimental", "Experimental"),
        ("production", "Production"),
        ("deprecated", "Deprecated"),
    ]

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="component_details",
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    lifecycle = models.CharField(max_length=32, choices=LIFECYCLE_CHOICES)
    system = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.PROTECT, related_name="components"
    )
    provides_apis = models.ManyToManyField(
        CATALOG_ENTITY_LABEL, related_name="provided_by", blank=True
    )
    consumes_apis = models.ManyToManyField(
        CATALOG_ENTITY_LABEL, related_name="consumed_by", blank=True
    )
    depends_on = models.ManyToManyField(
        CATALOG_ENTITY_LABEL, related_name="depended_on_by", blank=True
    )

    class Meta:
        # Kept on the pre-existing `catalog` app_label so this physical package
        # move needs no new migration — `catalog`'s existing migration history
        # already created this table.
        app_label = "catalog"

    def __str__(self) -> str:
        return self.entity.name
