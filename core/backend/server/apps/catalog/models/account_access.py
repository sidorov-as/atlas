from django.conf import settings
from django.db import models


class AccountAccess(models.Model):
    """Operator-managed account-wide write restriction: a side-car O2O on
    `settings.AUTH_USER_MODEL`,
    not a replacement User model. A missing row means `read_only=False`
    for compatibility — see `server.apps.catalog.authorization.
    is_account_read_only`, the shared predicate every guard consults;
    this model only stores the state, it does not itself enforce anything.
    """

    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_access",
    )
    read_only = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.account}: read_only={self.read_only}"


class AccountAccessAuditRecord(models.Model):
    """Append-only audit trail for `AccountAccess` changes (catalog-auth
    spec: "record operator, target, old/new values, and timestamp
    atomically with the change"). `target_id`/`target_username` are plain
    fields rather than a FK, mirroring `EntityAuditRecord.entity_id` — the
    record must stay readable even if the target account is later removed.
    """

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
    ]

    target_id = models.PositiveBigIntegerField(db_index=True)
    target_username = models.CharField(max_length=150)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    old_read_only = models.BooleanField(null=True)
    new_read_only = models.BooleanField(null=True)
    reason = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return (
            f"{self.action} AccountAccess for {self.target_username} "
            f"(id={self.target_id})"
        )
