from django.db import models


class PendingChange(models.Model):
    """A document whose index entry may be out of date.

    Written inside the transaction of the change that caused it, so a
    rolled-back write leaves nothing behind. One row per document id: a
    repeated change bumps `generation` instead of adding a row, and the
    indexer deletes a row only while its generation is still the one it read,
    so a change that lands mid-run stays pending.
    """

    document_id = models.CharField(max_length=512, unique=True)
    generation = models.PositiveIntegerField(default=1)
    queued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return self.document_id


class IndexStatus(models.Model):
    """Singleton (`pk=1`): what the indexing jobs last did."""

    last_drain_at = models.DateTimeField(null=True, blank=True)
    last_rebuild_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error_job = models.CharField(max_length=16, blank=True, default="")
    """`drain` or `rebuild`: only a success of the same job clears the error."""

    def __str__(self) -> str:
        return "search index status"
