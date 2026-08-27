from atlas_plugin_api import DEFAULT_TAG_COLOR, TAG_PALETTE
from atlas_plugin_api.tags import ensure_tags_exist
from django.db import models

# TAG_PALETTE/DEFAULT_TAG_COLOR/ensure_tags_exist are re-exported here (not
# redefined) so `atlas_plugin_api` stays their single source of truth
# every plugin imports them from
# `atlas_plugin_api`, and Core does too, rather than two copies risking drift
# (matching `models/base.py`'s
# equivalent note for `KIND_CHOICES`/`SOURCE_*`).
__all__ = ["DEFAULT_TAG_COLOR", "TAG_PALETTE", "Tag", "ensure_tags_exist"]


class Tag(models.Model):
    """A color assignment for a tag string, admin-managed.

    Auto-`get_or_create`d wherever an entity's `tags` array is written (manual
    PATCH, ingestion upsert) rather than pre-registered, so the Settings page
    always reflects exactly the tags currently in use.
    New rows default to `DEFAULT_TAG_COLOR` until an admin recolors them.

    `color` stores a palette key (e.g. `"blue"`), not a hex value — the
    frontend pairs each key with a bg/fg CSS token guaranteed to be
    readable together, so arbitrary hex values are no longer accepted.
    """

    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(
        max_length=32,
        choices=[(key, key) for key in TAG_PALETTE],
        default=DEFAULT_TAG_COLOR,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
