from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.db import models


class GroupDetails(models.Model):
    """Kind-specific data for a `CatalogEntity` of kind `group`.

    UI nav says "Teams" because `team` is the common `type` in practice (CONTEXT.md).
    `members`/`memberOf` is a single M2M, serialized from both ends, so the two
    sides can never disagree. `members` targets
    `CatalogEntity` directly (filtered to `kind=user` in application code) so
    both this row and the Actor's reverse lookups work with real entity ids.
    """

    TYPE_CHOICES: ClassVar[list] = [
        ("team", "Team"),
        ("business-unit", "Business unit"),
        ("product-area", "Product area"),
        ("root", "Root"),
    ]

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="group_details",
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    members = models.ManyToManyField(
        CATALOG_ENTITY_LABEL,
        related_name="member_of",
        through="catalog.GroupMembershipGrant",
        through_fields=("group", "actor"),
        blank=True,
    )

    class Meta:
        app_label = "catalog"

    def __str__(self) -> str:
        return self.entity.name
