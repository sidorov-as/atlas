from django.db import models

from .base import CatalogEntity


class Relation(models.Model):
    """A derived, typed edge between two catalog entities.

    Not directly writable — see `apps.catalog.relations.recompute_relations`,
    which is the only place rows are created or deleted. Both directions of a
    relation are materialized as separate rows (e.g. a `dependsOn` row and its
    `dependencyOf` mirror) so either entity's endpoint can list its relations
    with a single `subject`-or-`object` filter, no fan-out query.

    `subject_entity`/`object_entity` are real FKs to `CatalogEntity.id`
    replacing the old polymorphic
    `(kind, local_id)` pairs — a relation resolves unambiguously with no
    per-kind numbering to disambiguate.
    """

    subject_entity = models.ForeignKey(
        CatalogEntity,
        on_delete=models.CASCADE,
        related_name="relations_as_subject",
    )
    predicate = models.CharField(max_length=32)
    object_entity = models.ForeignKey(
        CatalogEntity,
        on_delete=models.CASCADE,
        related_name="relations_as_object",
    )

    class Meta:
        indexes = [
            models.Index(fields=["subject_entity", "predicate"]),
            models.Index(fields=["object_entity", "predicate"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["subject_entity", "predicate", "object_entity"],
                name="catalog_relation_unique_edge",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.subject_entity_id} {self.predicate} {self.object_entity_id}"
        )
