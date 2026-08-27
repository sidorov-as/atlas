from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.conf import settings
from django.db import models


class ActorDetails(models.Model):
    """Kind-specific data for a `CatalogEntity` of kind `user`.

    Renamed from the old concrete `User` model to `Actor` to resolve a naming collision with Authentication
    Core's later `Principal`/session concept — the *stored* `kind` value stays
    `"user"` (see `base.KIND_ACTOR`) so refs/wire responses are unaffected.

    Admin/ingestion-managed only, never ingested from YAML (CONTEXT.md). Distinct
    from `django.contrib.auth`'s login account, which allauth manages separately.
    `account` links the two so ownership permission checks can
    resolve a logged-in session to its Group memberships. `memberOf` is read
    from `GroupDetails.members` in reverse — see refs.py and GroupDetails above.
    """

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="actor_details",
    )
    display_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="catalog_actor",
    )

    class Meta:
        app_label = "catalog"

    def __str__(self) -> str:
        return self.entity.name
