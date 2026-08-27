from django.conf import settings
from django.db import models


class AuthenticationSourceBinding(models.Model):
    """Persisted, generation-bearing binding to one identity authority."""

    provider_id = models.CharField(max_length=128)
    source_id = models.CharField(max_length=512)
    configuration_fingerprint = models.CharField(max_length=255)
    lock_digest = models.CharField(max_length=255, blank=True, default="")
    generation = models.PositiveBigIntegerField(default=1)
    activated_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider_id", "source_id"),
                name="catalog_unique_auth_source_binding",
            )
        ]


class AuthenticationPolicyState(models.Model):
    """Singleton generation for the currently selected authentication policy."""

    digest = models.CharField(max_length=64)
    generation = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)


class AuthenticationPrincipalState(models.Model):
    """Durable per-Principal revoke-all generation."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authentication_state",
    )
    revocation_generation = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class AuthenticationRateLimit(models.Model):
    """Cross-worker authentication abuse budget."""

    key_hash = models.CharField(max_length=64, primary_key=True)
    scope = models.CharField(max_length=32, db_index=True)
    window_started_at = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class ProvisioningAuditRecord(models.Model):
    """Append-only, allowlist-shaped audit for successful identity changes."""

    action = models.CharField(max_length=64)
    provider_id = models.CharField(max_length=128)
    source_id = models.CharField(max_length=512)
    principal_id = models.PositiveBigIntegerField(
        null=True, blank=True, db_index=True
    )
    identity_link_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_id = models.UUIDField(null=True, blank=True)
    group_id = models.UUIDField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, db_index=True)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp",)


class AuthenticationSecurityEvent(models.Model):
    """Durable sanitized failure/denial event written outside rollback scope."""

    category = models.CharField(max_length=64)
    stage = models.CharField(max_length=64, default="provisioning")
    provider_id = models.CharField(max_length=128)
    source_id = models.CharField(max_length=512)
    correlation_id = models.CharField(max_length=64, db_index=True)
    principal_id = models.PositiveBigIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-timestamp",)
