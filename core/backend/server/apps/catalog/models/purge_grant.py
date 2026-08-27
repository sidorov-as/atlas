from django.conf import settings
from django.db import models

from .base import CatalogEntity


class PurgeGrant(models.Model):
    """Purge Grant permission: scoped per owner-Group, it authorizes
    `grantee` to Purge
    a `removed` entity owned by `group` — a narrow, explicit carve-out from
    the otherwise-uniform ownership-based write rule, since Purge is
    destructive/irreversible and (unlike Remove/Revive) is also allowed on
    `source_kind=yaml` entities. Global-admin (`is_superuser`) status is
    recognized as an override wherever a grant is checked
    (`authorization.has_purge_grant`) rather than being modeled as a row
    here — there is no per-group "admin" role in this codebase today, so
    `granted_by` is a record of who assigned the grant (managed via Django
    admin), not itself part of the authorization check.
    """

    group = models.ForeignKey(
        CatalogEntity,
        on_delete=models.CASCADE,
        related_name="purge_grants",
    )
    grantee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purge_grants",
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "grantee"],
                name="purge_grant_unique_group_grantee",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.grantee} may purge entities owned by {self.group}"
