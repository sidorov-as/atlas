import hashlib
import secrets

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.conf import settings
from django.db import models
from django.utils import timezone

_TOKEN_NBYTES = 32


def generate_upload_token() -> str:
    """256 bits from the OS CSPRNG, URL-safe."""
    return secrets.token_urlsafe(_TOKEN_NBYTES)


def hash_upload_token(token: str) -> str:
    """Plain SHA-256: the token is high-entropy and random, so a fast hash
    carries no offline-guessing risk (same reasoning as PAT hashing)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class UploadTicket(models.Model):
    """A short-lived, single-use capability to `PUT` one file into one field
    of one entity (`upload-tickets` spec). Only the token's hash is stored;
    the token itself is returned once, at issuance.
    """

    token_hash = models.CharField(max_length=64, unique=True)
    entity = models.ForeignKey(
        CATALOG_ENTITY_LABEL,
        on_delete=models.CASCADE,
        related_name="upload_tickets",
    )
    field = models.CharField(max_length=64)
    params = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upload_tickets",
    )
    personal_access_token = models.ForeignKey(
        "catalog.PersonalAccessToken",
        on_delete=models.CASCADE,
        related_name="upload_tickets",
    )
    expires_at = models.DateTimeField(db_index=True)
    max_bytes = models.PositiveBigIntegerField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.entity_id}:{self.field} ({self.expires_at:%H:%M:%S})"

    def is_usable(self) -> bool:
        """Unconsumed, unexpired, and issued by a PAT that is still valid
        (not revoked/expired, owner active)."""
        if self.consumed_at is not None or self.expires_at <= timezone.now():
            return False
        return self.personal_access_token.is_currently_valid()
