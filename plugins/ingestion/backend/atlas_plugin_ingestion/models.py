import re
from pathlib import PurePosixPath
from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL, INGESTION_CLAIM_ACCESSOR
from django.core.exceptions import ValidationError
from django.db import models

_CONTROL_OR_WHITESPACE_RE = re.compile(r"[\x00-\x1f\x7f\s]")


def validate_repository_path(path: str) -> None:
    """Reject a `RegisteredRepository.path` that could escape or override
    its source's `baseUrl` when naively concatenated — `path` is validated
    directly rather than the assembled URL, to prevent URL injection."""
    if not path:
        raise ValidationError("Path must not be empty.", code="empty")
    if path.startswith("/"):
        raise ValidationError(
            'Path must not begin with "/".',
            code="leading_slash",
        )
    if ".." in PurePosixPath(path).parts:
        raise ValidationError(
            'Path must not contain ".." segments.',
            code="path_traversal",
        )
    if _CONTROL_OR_WHITESPACE_RE.search(path):
        raise ValidationError(
            "Path must not contain control or whitespace characters.",
            code="invalid_characters",
        )
    if "://" in path:
        raise ValidationError(
            'Path must not contain "://".',
            code="scheme_like",
        )


class ConflictRecord(models.Model):
    """A rejected ingestion claim (ADR 0001 amendment).

    Created/updated whenever an ingestion run's claim on `(kind, namespace,
    name)` is rejected because the ref is already claimed by a manual entity
    or a different repository. `repository` is nullable and `repo_full_name`
    is a plain-string snapshot taken at write time, so a repository can be
    deleted (once it claims no entities) without losing conflict history or
    letting historical conflicts block that deletion.
    """

    REASON_MANUAL_ENTITY = "manual_entity"
    REASON_OTHER_REPOSITORY = "other_repository"
    REASON_REMOVED_ENTITY = "removed_entity"
    REASON_CHOICES: ClassVar[list] = [
        (REASON_MANUAL_ENTITY, "Claimed by a manual entity"),
        (REASON_OTHER_REPOSITORY, "Claimed by a different repository"),
        (REASON_REMOVED_ENTITY, "Claimed by a removed entity"),
    ]

    repository = models.ForeignKey(
        "RegisteredRepository",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conflict_records",
    )
    repo_full_name = models.CharField(max_length=255)
    kind = models.CharField(max_length=32)
    namespace = models.CharField(max_length=255, default="default")
    name = models.CharField(max_length=255)
    reason = models.CharField(max_length=32, choices=REASON_CHOICES)
    is_active = models.BooleanField(default=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list] = ["-last_seen"]

    def __str__(self) -> str:
        return f"{self.kind}:{self.namespace}/{self.name} blocked for {self.repo_full_name}"


class IngestionIssue(models.Model):
    """A non-claim-conflict ingestion-time problem for a `(repository, path)`
    (manifest-processing failures are persisted and admin-visible).

    Covers everything `ConflictRecord` doesn't: connector fetch failures,
    YAML parse failures, manifest schema-validation failures, and
    `Include`-specific failures (unresolved/empty path or glob, fetch
    failure, cycle detection, an included fragment named
    `catalog-info.yaml`). `message` is the same human-readable string that
    already goes to `logger.warning`/`.exception` — no typed `reason` (v1
    scope). `repository` is nullable/`SET_NULL` and
    `repo_full_name` is a plain-string snapshot, mirroring `ConflictRecord`,
    so a repository can be deleted without losing issue history.
    """

    repository = models.ForeignKey(
        "RegisteredRepository",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ingestion_issues",
    )
    repo_full_name = models.CharField(max_length=255)
    path = models.CharField(max_length=1024, blank=True)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list] = ["-last_seen"]

    def __str__(self) -> str:
        return f"{self.repo_full_name}:{self.path}"


class RegisteredRepository(models.Model):
    """Operational config for a repo the ingestor polls (deployment-level
    `sources` in plugin config).

    `source_id` references a source declared in `atlas.ingestion` plugin
    config, resolved once at process startup — not a database-level
    `ForeignKey`, since sources live in resolved plugin config, not a
    database table); validated against the
    currently resolved config in Django admin instead (`admin.py`). `path`
    is this repository's path relative to that source's `baseUrl`. No
    ingestion credential is stored here or anywhere else in the database.

    Not a catalog entity itself (`Location` is out of scope) — managed via
    Django admin, not the entity CRUD API.
    """

    source_id = models.CharField(
        max_length=255,
        help_text="References a source id declared in atlas.ingestion plugin config",
    )
    path = models.CharField(
        max_length=1024,
        help_text="Repository path relative to the source's baseUrl",
    )
    default_branch = models.CharField(max_length=255, default="main")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list] = ["source_id", "path"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["source_id", "path"],
                name="unique_registered_repository_source_path",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        validate_repository_path(self.path)

    def __str__(self) -> str:
        return f"{self.source_id}/{self.path}"


class EntityClaim(models.Model):
    """Which repository claims a catalog entity (`source_kind=yaml`).

    Owned by this plugin, not by the core entity row: core's schema carries
    no reference to ingestion, so a distribution that doesn't select this
    plugin has no ingestion tables and migrates cleanly. The reverse accessor
    on the entity is `INGESTION_CLAIM_ACCESSOR`, which `atlas_plugin_api`'s
    `ingested_from()` reads.

    `repository` is `PROTECT`: a repository can't be unregistered while it
    claims any entity, active or `removed`. Purging the entity deletes its
    claim (`CASCADE`).
    """

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        on_delete=models.CASCADE,
        related_name=INGESTION_CLAIM_ACCESSOR,
    )
    repository = models.ForeignKey(
        RegisteredRepository,
        on_delete=models.PROTECT,
        related_name="claims",
    )

    def __str__(self) -> str:
        return f"{self.entity_id} claimed by {self.repository}"
