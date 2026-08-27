from django.db import models


class AuthenticationAttempt(models.Model):
    """One Core-owned, browser-bound redirect authentication transaction."""

    provider_id = models.CharField(max_length=128)
    source_id = models.CharField(max_length=512)
    state_digest = models.CharField(max_length=64, unique=True, null=True)
    browser_session_digest = models.CharField(max_length=64)
    return_url = models.TextField()
    correlation_id = models.UUIDField()
    policy_generation = models.PositiveBigIntegerField(default=1)
    source_generation = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("provider_id", "expires_at"),
                name="catalog_auth_attempt_expiry",
            ),
        ]
