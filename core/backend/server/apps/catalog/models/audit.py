from django.conf import settings
from django.db import models


class EntityAuditRecord(models.Model):
    """Append-only entity lifecycle audit trail.

    Written by `EntityService` in the same transaction as the `CatalogEntity`
    change it records. `entity_id` is a plain UUID, not a FK — a `delete`
    record must survive the `CatalogEntity` row it refers to, and a durable
    trail can't be allowed to vanish along with the entity it's about
    Kept intentionally minimal: this is *a*
    durable trail satisfying the pipeline contract, not a full audit-log
    product — no retention policy or query UI.
    """

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_REMOVE = "remove"
    ACTION_REVIVE = "revive"
    ACTION_PURGE = "purge"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
        (ACTION_REMOVE, "Remove"),
        (ACTION_REVIVE, "Revive"),
        (ACTION_PURGE, "Purge"),
    ]

    entity_id = models.UUIDField(db_index=True)
    kind = models.CharField(max_length=32)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    diff = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.action} {self.kind}:{self.entity_id}"
