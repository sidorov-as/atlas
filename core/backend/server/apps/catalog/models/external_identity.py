from django.conf import settings
from django.db import models


class ExternalIdentityLink(models.Model):
    """Maps an `ExternalIdentity` an authentication provider has confirmed
    control over to the stable `Principal` it resolves to.

    `atlas.auth.local` needs no such table because its stable subject is an
    existing local Principal id. Redirect and third-party providers do: their
    source-bound subject has no other safe mapping to a Principal. This table
    is owned by Core provisioning, independent of provider-library storage.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="external_identity_links",
    )
    provider_id = models.CharField(max_length=64)
    source_id = models.CharField(max_length=512, blank=True, default="")
    external_subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_generation = models.PositiveBigIntegerField(default=0)
    last_applied_generation = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider_id", "source_id", "external_subject"],
                name="catalog_unique_external_identity_source",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider_id}:{self.external_subject} -> {self.user_id}"
