import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

TOKEN_SECRET_PREFIX = "atlaspat_"
"""Plaintext prefix so a leaked/pasted Atlas PAT is recognizable at a glance
(matches the convention of e.g. GitHub's `ghp_`/`github_pat_` tokens) —
part of the plaintext value shown once at issuance, not stored."""

LOOKUP_PREFIX_LENGTH = 8
"""Length of the short, non-secret lookup prefix stored alongside the hash
(`personal-access-tokens` spec: "hash + short lookup prefix, never
plaintext at rest") — narrows `token_hash` lookup to (in practice) a
single row without needing the hash itself to be indexable in a way that
leaks timing information about which prefix matched."""

_SECRET_NBYTES = 32


def generate_token_secret() -> str:
    """A new, URL-safe random secret — the part of the plaintext token that
    follows `TOKEN_SECRET_PREFIX`. Never stored; only its hash is."""
    return secrets.token_urlsafe(_SECRET_NBYTES)


def hash_token_secret(secret: str) -> str:
    """Deterministic, unsalted-but-high-entropy hash of a token secret.

    A per-token random salt (as for a password) would defeat the
    prefix+hash lookup this model relies on for validation (`personal-
    access-tokens` spec's `expires_at`/`revoked_at` checks need a single
    indexed row, not a scan-and-compare over every live token) — safe here
    specifically because the input is a high-entropy, randomly generated
    secret rather than a human-chosen password, so a plain fast hash carries
    none of a password hash's offline-guessing risk.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class PersonalAccessToken(models.Model):
    """An Atlas Personal Access Token (`personal-access-tokens` spec): a
    Bearer credential a user issues for themselves, carrying one or more
    scopes that narrow — never broaden — their own RBAC, with
    `expires_at`/`revoked_at`/`last_used_at`. Stored as a salted-by-entropy
    hash (`token_hash`) plus a short `prefix` for lookup; the plaintext is
    shown exactly once, at issuance (`services.pat_service.
    issue_personal_access_token`), and never persisted anywhere.
    """

    SCOPE_CATALOG_READ = "catalog:read"
    SCOPE_CATALOG_WRITE = "catalog:write"
    SCOPE_FLOWS_READ = "flows:read"
    SCOPE_FLOWS_WRITE = "flows:write"
    SCOPE_CHOICES = [
        (SCOPE_CATALOG_READ, "Catalog: read"),
        (SCOPE_CATALOG_WRITE, "Catalog: write"),
        (SCOPE_FLOWS_READ, "Flows: read"),
        (SCOPE_FLOWS_WRITE, "Flows: write"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_access_tokens",
    )
    name = models.CharField(max_length=255, blank=True, default="")
    prefix = models.CharField(max_length=LOOKUP_PREFIX_LENGTH, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        scopes = ", ".join(self.scopes) or "no scopes"
        return f"{self.owner}: {self.prefix}… ({scopes})"

    def is_currently_valid(self) -> bool:
        """`personal-access-tokens` spec: rejects a token whose `expires_at`
        has passed, whose `revoked_at` is set, or whose owning account is
        no longer active — independent of the token's own fields for the
        last case."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return False
        return bool(self.owner.is_active)
