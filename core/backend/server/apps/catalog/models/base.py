import uuid

from atlas_plugin_api import (
    DETAILS_RELATED_NAME,
    KIND_CHOICES,
    SOURCE_KIND_CHOICES,
    SOURCE_MANUAL,
    SOURCE_YAML,
    STATUS_ACTIVE,
    STATUS_CHOICES,
    STATUS_REMOVED,
)
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Lower

# KIND_*/SOURCE_*/DETAILS_RELATED_NAME/INGESTIBLE_KINDS/KIND_CHOICES/
# SOURCE_KIND_CHOICES are re-exported here (not redefined) so `atlas_plugin_api`
# stays their single source of truth —
# every plugin imports them from `atlas_plugin_api`, and Core does too, rather
# than two copies risking drift. Stored/ref-visible kind stays "user": the
# User -> Actor rename
# is a Python-identifier rename only (avoids a naming collision with
# Authentication Core's later `Principal` concept); this doesn't change
# any REST route or response field besides adding `id`, and
# `.ref`/`target_kind` embed `kind` verbatim in wire responses, so the stored
# value can't move to "actor" here.


class CatalogEntity(models.Model):
    """The single concrete identity row for every catalog entity kind
    (ADR 0001).

    Kind-specific data never lives here — it lives in a `OneToOne` "details"
    model per kind (`SystemDetails`, `ComponentDetails`, `ResourceDetails`,
    `ApiDetails`, `GroupDetails`, `ActorDetails`), reachable via `.details` or
    the kind-specific reverse accessor named in `DETAILS_RELATED_NAME`.
    `id` is a UUID (not the old per-kind integer PK) so it stays stable and
    globally comparable even across a details row disappearing entirely.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    name = models.CharField(max_length=255)
    namespace = models.CharField(max_length=255, default="default")
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    documentation = models.TextField(blank=True)
    labels = models.JSONField(default=dict, blank=True)
    tags = ArrayField(
        models.CharField(max_length=100), default=list, blank=True
    )
    links = models.JSONField(default=list, blank=True)
    # `on_delete=SET_NULL`, not `PROTECT`: deleting an owner is guarded at the
    # application level instead (kind handlers' `validate_delete`, per
    # the "owner protected-reference" rule), since only
    # an *active*-status owned entity should block the delete — a status-
    # blind DB-level `PROTECT` can't express that, and would keep blocking
    # deletion of an owner whose only remaining owned entities are `removed`.
    owner = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_entities",
    )

    # Provenance — every entity
    # carries these now, not just the kinds ingestion can claim; Group/Actor
    # simply never leave `source_kind=manual`. Values come from
    # `atlas_plugin_api` (see module-level re-export note above); kept as
    # class attributes too since `CatalogEntity.SOURCE_YAML`-style access is
    # relied on throughout Core.
    SOURCE_MANUAL = SOURCE_MANUAL
    SOURCE_YAML = SOURCE_YAML
    SOURCE_KIND_CHOICES = SOURCE_KIND_CHOICES
    source_kind = models.CharField(
        max_length=16, choices=SOURCE_KIND_CHOICES, default=SOURCE_MANUAL
    )

    # Removed/Revive/Purge lifecycle —
    # decoupled from any `deprecated`/`lifecycle` cosmetic flag a kind's
    # details may carry; `removed` never deletes this row, `Purge` does.
    STATUS_ACTIVE = STATUS_ACTIVE
    STATUS_REMOVED = STATUS_REMOVED
    STATUS_CHOICES = STATUS_CHOICES
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "namespace",
                "kind",
                name="catalog_entity_unique_kind_namespace_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def ref(self) -> str:
        """Computed `kind:name` representation — see the shared resolver in
        refs.py."""
        return f"{self.kind}:{self.name}"

    @property
    def details(self):
        """This entity's kind-specific details row (e.g. `ComponentDetails`
        for a Component)."""
        return getattr(self, DETAILS_RELATED_NAME[self.kind])
