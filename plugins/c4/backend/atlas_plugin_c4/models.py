import uuid
from typing import ClassVar

from django.db import models
from django.db.models.functions import Lower


class View(models.Model):
    """A saved C4 custom view: a named slice of the catalog.

    Not a `CatalogEntity`. `settings` holds the rules (level, selection mode,
    entity UUIDs, depth, direction, entity types, relationship source) in the
    shape of `api.schemas.CustomViewSettings`; entities are referenced by UUID
    inside the JSON, not by foreign key, so a view can outlive an entity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(Lower("name"), name="c4_view_name_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.name
