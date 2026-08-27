from django.conf import settings
from django.db import models
from django.utils import timezone


class GroupMembershipGrant(models.Model):
    """One independently removable reason for an Actor to belong to a Group."""

    SOURCE_MANUAL = "manual"
    SOURCE_PROVIDER = "provider"
    SOURCE_CHOICES = (
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_PROVIDER, "Authentication provider"),
    )

    group = models.ForeignKey(
        "catalog.GroupDetails",
        on_delete=models.CASCADE,
        related_name="membership_grants",
    )
    actor = models.ForeignKey(
        "catalog.CatalogEntity",
        on_delete=models.CASCADE,
        related_name="membership_grants",
    )
    source_kind = models.CharField(
        max_length=16,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
    )
    identity_link = models.ForeignKey(
        "catalog.ExternalIdentityLink",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="membership_grants",
    )
    external_key = models.CharField(max_length=512, blank=True, default="")
    legacy_unclassified = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_confirmed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        source_kind="manual",
                        identity_link__isnull=True,
                        external_key="",
                        expires_at__isnull=True,
                    )
                    | models.Q(
                        source_kind="provider",
                        identity_link__isnull=False,
                        legacy_unclassified=False,
                    )
                ),
                name="catalog_membership_grant_source_shape",
            ),
            models.UniqueConstraint(
                fields=("group", "actor"),
                condition=models.Q(source_kind="manual"),
                name="catalog_unique_manual_membership_grant",
            ),
            models.UniqueConstraint(
                fields=("group", "actor", "identity_link", "external_key"),
                condition=models.Q(source_kind="provider"),
                name="catalog_unique_provider_membership_grant",
            ),
        ]
        indexes = [
            models.Index(
                fields=("actor", "group"),
                name="catalog_grant_actor_group",
            ),
            models.Index(
                fields=("group", "actor", "expires_at"),
                name="catalog_grant_group_expiry",
            ),
            models.Index(
                fields=("identity_link", "external_key"),
                name="catalog_grant_link_key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.actor_id} -> {self.group_id} ({self.source_kind})"


class MembershipGrantAuditRecord(models.Model):
    """Append-only operator trail for membership provenance changes."""

    ACTION_CLASSIFY_MANUAL = "classify_manual"
    ACTION_TRANSFER_PROVIDER = "transfer_provider"
    ACTION_CHOICES = (
        (ACTION_CLASSIFY_MANUAL, "Classify as manual"),
        (ACTION_TRANSFER_PROVIDER, "Transfer to provider"),
    )

    grant_id = models.PositiveBigIntegerField(db_index=True)
    group_id = models.UUIDField(db_index=True)
    actor_id = models.UUIDField(db_index=True)
    identity_link_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reason = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-timestamp",)


class LegacyGroupMembershipPair(models.Model):
    """Rollback shadow for the pre-grant implicit M2M table.

    Runtime membership never reads this table. Keeping it represented in
    migration/model state lets Django flush and reverse migrations manage its
    foreign keys safely until the compatibility window closes.
    """

    groupdetails = models.ForeignKey(
        "catalog.GroupDetails",
        db_column="groupdetails_id",
        on_delete=models.CASCADE,
    )
    catalogentity = models.ForeignKey(
        "catalog.CatalogEntity",
        db_column="catalogentity_id",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "catalog_groupdetails_members"
        unique_together = (("groupdetails", "catalogentity"),)
