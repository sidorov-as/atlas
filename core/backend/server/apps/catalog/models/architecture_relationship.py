from atlas_plugin_api import (
    ARCHITECTURE_RELATIONSHIP_ORIGIN_MANUAL,
    ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML,
)
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q

from .base import CatalogEntity


class ArchitectureRelationship(models.Model):
    """A declared, directed architecture interaction between catalog entities.

    Unlike :class:`Relation`, these rows represent authored runtime intent and
    are never regenerated from entity specifications.

    `source`/`target` are real FKs to `CatalogEntity.id`
    replacing the old polymorphic
    `(kind, local_id)` pairs — `source.kind`/`target.kind` are derived from the
    referenced entity rather than stored redundantly.
    """

    class InteractionKind(models.TextChoices):
        SYNCHRONOUS = "synchronous", "Synchronous"
        ASYNCHRONOUS = "asynchronous", "Asynchronous"
        DATA_ACCESS = "data-access", "Data access"
        MANUAL = "manual", "Manual"

    class Origin(models.TextChoices):
        MANUAL = ARCHITECTURE_RELATIONSHIP_ORIGIN_MANUAL, "Manual"
        YAML = ARCHITECTURE_RELATIONSHIP_ORIGIN_YAML, "YAML"

    source = models.ForeignKey(
        CatalogEntity,
        on_delete=models.CASCADE,
        related_name="architecture_relationships_as_source",
    )
    target = models.ForeignKey(
        CatalogEntity,
        on_delete=models.CASCADE,
        related_name="architecture_relationships_as_target",
    )
    label = models.CharField(max_length=255)
    technology = models.CharField(max_length=255, blank=True)
    interaction_kind = models.CharField(
        max_length=16,
        choices=InteractionKind,
        default=InteractionKind.MANUAL,
    )
    tags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )
    origin = models.CharField(
        max_length=16,
        choices=Origin,
        default=Origin.MANUAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["source"]),
            models.Index(fields=["target"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(label=""),
                name="catalog_architecture_relationship_label_nonempty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source_id} -> {self.target_id}: {self.label}"
