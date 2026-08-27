"""Atomic provider-independent identity provisioning and reconciliation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

from atlas_plugin_api import (
    KIND_GROUP,
    ActorProvisioningRequest,
    AttributeProvenance,
    ExternalGroupSnapshotStatus,
    VerifiedIdentity,
    get_actor_provisioning_service,
)
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from .auth_security import redact_authentication_data
from .membership import add_provider_membership
from .models import (
    AuthenticationSecurityEvent,
    AuthenticationSourceBinding,
    CatalogEntity,
    ExternalIdentityLink,
    GroupMembershipGrant,
    ProvisioningAuditRecord,
)

SAFE_PROFILE_FIELDS = frozenset({"username", "displayName", "email"})


class ProvisioningError(RuntimeError):
    category = "provisioning_failed"


class IdentityConflictError(ProvisioningError):
    category = "identity_conflict"


class EligibilityError(ProvisioningError):
    category = "ineligible_identity"


class StaleAuthenticationAttemptError(ProvisioningError):
    category = "stale_authentication_attempt"


@dataclass(frozen=True, slots=True)
class ProvisioningResult:
    user: Any
    identity_link: ExternalIdentityLink
    actor_id: Any | None


def _audit(
    action: str,
    *,
    identity: VerifiedIdentity,
    correlation_id: str,
    user=None,
    link=None,
    actor_id=None,
    group_id=None,
    details: dict[str, Any] | None = None,
) -> None:
    ProvisioningAuditRecord.objects.create(
        action=action,
        provider_id=identity.provider_id,
        source_id=identity.source_id,
        principal_id=getattr(user, "pk", None),
        identity_link_id=getattr(link, "pk", None),
        actor_id=actor_id,
        group_id=group_id,
        correlation_id=correlation_id,
        details=redact_authentication_data(details or {}),
    )


def _security_event(
    error: Exception,
    *,
    identity: VerifiedIdentity,
    correlation_id: str,
) -> None:
    AuthenticationSecurityEvent.objects.create(
        category=getattr(error, "category", "provisioning_failed"),
        provider_id=identity.provider_id,
        source_id=identity.source_id,
        correlation_id=correlation_id,
        details=redact_authentication_data(
            {"exceptionType": type(error).__name__}
        ),
    )


def _source_binding(identity: VerifiedIdentity, policy: dict[str, Any]):
    configured = policy.get("sourceBinding")
    if not isinstance(configured, dict):
        raise ProvisioningError("provider has no source binding")
    source_id = configured.get("sourceId")
    fingerprint = configured.get("configurationFingerprint")
    if (
        source_id != identity.source_id
        or not isinstance(fingerprint, str)
        or not fingerprint
    ):
        raise ProvisioningError(
            "identity source does not match configured binding"
        )
    binding, created = (
        AuthenticationSourceBinding.objects.select_for_update().get_or_create(
            provider_id=identity.provider_id,
            source_id=identity.source_id,
            defaults={
                "configuration_fingerprint": fingerprint,
                "lock_digest": str(configured.get("lockDigest", "")),
            },
        )
    )
    if binding.revoked_at is not None:
        raise ProvisioningError("identity source binding is revoked")
    if not created and binding.configuration_fingerprint != fingerprint:
        raise IdentityConflictError(
            "identity authority changed; use a new source or reviewed migration"
        )
    return binding


def _eligible(identity: VerifiedIdentity, policy: dict[str, Any]) -> bool:
    for requirement in policy.get("restrictedAttributes", ()):
        if not isinstance(requirement, dict):
            return False
        name = requirement.get("name")
        if not isinstance(name, str):
            return False
        attribute = identity.attributes.get(name)
        if attribute is None:
            return False
        accepted = {
            str(value).replace("-", "_")
            for value in requirement.get("acceptedProvenance", ())
        }
        if attribute.provenance.value not in accepted:
            return False
        accepted_values = requirement.get("acceptedValues") or requirement.get(
            "values"
        )
        if accepted_values and attribute.value.casefold() not in {
            str(value).strip().casefold() for value in accepted_values
        }:
            return False
        allowed_domains = requirement.get("allowedDomains")
        if allowed_domains:
            if (
                attribute.provenance
                is not AttributeProvenance.VERIFIED_OWNERSHIP
            ):
                return False
            _local, separator, domain = (
                attribute.value.strip().casefold().rpartition("@")
            )
            if not separator or domain not in {
                str(value).strip().casefold() for value in allowed_domains
            }:
                return False
    return True


def _unique_username(identity: VerifiedIdentity) -> str:
    user_model = get_user_model()
    base = slugify(identity.profile.username or "")[:120]
    if not base:
        digest = hashlib.sha256(
            f"{identity.provider_id}\0{identity.source_id}\0{identity.subject}".encode()
        ).hexdigest()[:16]
        base = f"external-{digest}"
    candidate = base
    suffix = 1
    while user_model.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f"{base[:140]}-{suffix}"
    return candidate


def _principal_and_link(
    identity: VerifiedIdentity,
    policy: dict[str, Any],
    *,
    correlation_id: str,
):
    user_model = get_user_model()
    link = (
        ExternalIdentityLink.objects.select_for_update()
        .select_related("user")
        .filter(
            provider_id=identity.provider_id,
            source_id=identity.source_id,
            external_subject=identity.subject,
        )
        .first()
    )
    if link is not None:
        if link.revoked_at is not None:
            raise IdentityConflictError("external identity link is revoked")
        if not link.user.is_active:
            raise EligibilityError("Principal is inactive")
        return link.user, link, False

    # Pre-source-binding OIDC rows used an empty source id. Never create a
    # second Principal beside one of those ambiguous historical links: an
    # operator must first verify the old authority and run source-migrate.
    if (
        ExternalIdentityLink.objects.select_for_update()
        .filter(
            provider_id=identity.provider_id,
            source_id="",
            external_subject=identity.subject,
        )
        .exists()
    ):
        raise IdentityConflictError(
            "historical identity link has no verified source; run the "
            "reviewed source-migrate workflow"
        )

    mode = policy.get("principalProvisioning", "preprovisioned")
    if mode == "preprovisioned":
        raise ProvisioningError("external identity is not preprovisioned")
    if mode not in {"automatic", "restricted"}:
        raise ProvisioningError("unsupported Principal provisioning policy")
    if mode == "restricted" and not _eligible(identity, policy):
        raise EligibilityError("identity does not satisfy restricted policy")

    user = user_model.objects.create_user(username=_unique_username(identity))
    user.set_unusable_password()
    user.save(update_fields=("password",))
    try:
        link = ExternalIdentityLink.objects.create(
            user=user,
            provider_id=identity.provider_id,
            source_id=identity.source_id,
            external_subject=identity.subject,
        )
    except IntegrityError as exc:
        raise IdentityConflictError(
            "external identity was linked concurrently"
        ) from exc
    _audit(
        "principal_created",
        identity=identity,
        correlation_id=correlation_id,
        user=user,
        link=link,
    )
    return user, link, True


def _apply_profile(
    user,
    identity: VerifiedIdentity,
    policy: dict[str, Any],
    *,
    correlation_id: str,
    link: ExternalIdentityLink,
) -> None:
    requested = set(policy.get("profileFields", ()))
    if not requested <= SAFE_PROFILE_FIELDS:
        raise ProvisioningError("profile policy contains protected fields")
    changed: list[str] = []
    if "username" in requested and identity.profile.username is not None:
        value = identity.profile.username
        if (
            get_user_model()
            .objects.exclude(pk=user.pk)
            .filter(username__iexact=value)
            .exists()
        ):
            raise IdentityConflictError("provider-managed username collides")
        if user.username != value:
            user.username = value
            changed.append("username")
    if (
        "email" in requested
        and identity.profile.email is not None
        and user.email != identity.profile.email
    ):
        user.email = identity.profile.email
        changed.append("email")
    if (
        "displayName" in requested
        and identity.profile.display_name is not None
        and user.first_name != identity.profile.display_name
    ):
        user.first_name = identity.profile.display_name
        changed.append("first_name")
    if changed:
        user.save(update_fields=changed)
        _audit(
            "profile_updated",
            identity=identity,
            correlation_id=correlation_id,
            user=user,
            link=link,
            details={"fields": sorted(requested & SAFE_PROFILE_FIELDS)},
        )


def _actor(user, identity, policy, *, correlation_id: str):
    service = get_actor_provisioning_service()
    existing = service.resolve_for_principal(user.pk)
    if (
        existing is None
        and policy.get("actorProvisioning", "manual") == "automatic"
    ):
        result = service.ensure_for_principal(
            ActorProvisioningRequest(
                principal_id=user.pk,
                proposed_name=identity.profile.username or user.username,
                display_name=identity.profile.display_name or "",
                email=identity.profile.email or "",
                correlation_id=correlation_id,
            )
        )
        existing = result.actor
        if result.created:
            _audit(
                "actor_created",
                identity=identity,
                correlation_id=correlation_id,
                user=user,
                actor_id=existing.id,
            )
    if existing is not None:
        requested = set(policy.get("profileFields", ()))
        service.update_profile(
            principal_id=user.pk,
            display_name=identity.profile.display_name
            if "displayName" in requested
            else None,
            email=identity.profile.email if "email" in requested else None,
        )
    return existing


def _mapped_groups(identity: VerifiedIdentity, policy: dict[str, Any]):
    config = policy.get("groupSync", {})
    mappings = {
        str(key).strip().casefold(): value
        for key, value in config.get("mappings", {}).items()
    }
    mapped: dict[str, tuple[str, Any]] = {}
    ignored = 0
    for external in identity.groups.groups:
        normalized = external.strip().casefold()
        target = mappings.get(normalized)
        if not target:
            ignored += 1
            continue
        entity = CatalogEntity.objects.filter(
            kind=KIND_GROUP,
            name__iexact=target,
            status=CatalogEntity.STATUS_ACTIVE,
        ).first()
        if entity is not None:
            mapped[normalized] = (
                external,
                cast(Any, entity).group_details,
            )
        else:
            ignored += 1
    return mapped, ignored


def _reconcile_groups(
    user, link, actor, identity, policy, *, correlation_id: str
):
    config = policy.get("groupSync", {})
    mode = config.get("mode", "none")
    if mode == "none":
        return
    requirement = config.get("snapshotRequirement", "best-effort")
    if identity.groups.status is not ExternalGroupSnapshotStatus.COMPLETE:
        if mode == "exact" or requirement == "required":
            raise ProvisioningError("complete group snapshot required")
        return
    if actor is None:
        raise ProvisioningError("group reconciliation requires a linked Actor")
    mapped, ignored = _mapped_groups(identity, policy)
    if ignored:
        _audit(
            "unknown_groups_ignored",
            identity=identity,
            correlation_id=correlation_id,
            user=user,
            link=link,
            actor_id=actor.id,
            details={"count": ignored},
        )
    max_age = config.get("maxAgeSeconds", 28_800)
    expires_at = (
        timezone.now() + timedelta(seconds=max_age) if mode == "exact" else None
    )
    retained: set[tuple[Any, str]] = set()
    actor_entity = CatalogEntity.objects.get(pk=actor.id)
    for normalized, (_external, group) in mapped.items():
        existed = GroupMembershipGrant.objects.filter(
            group=group,
            actor=actor_entity,
            identity_link=link,
            external_key=normalized,
        ).exists()
        grant = add_provider_membership(
            group=group,
            actor=actor_entity,
            identity_link=link,
            external_key=normalized,
            expires_at=expires_at,
        )
        retained.add((grant.group_id, grant.external_key))
        _audit(
            "grant_confirmed" if existed else "grant_added",
            identity=identity,
            correlation_id=correlation_id,
            user=user,
            link=link,
            actor_id=actor.id,
            group_id=grant.group_id,
            details={
                "externalKeyDigest": hashlib.sha256(
                    normalized.encode()
                ).hexdigest()
            },
        )
    if mode == "exact":
        stale = GroupMembershipGrant.objects.select_for_update().filter(
            identity_link=link,
            source_kind=GroupMembershipGrant.SOURCE_PROVIDER,
        )
        for grant in stale:
            if (grant.group_id, grant.external_key) not in retained:
                group_id = grant.group_id
                grant.delete()
                _audit(
                    "grant_removed",
                    identity=identity,
                    correlation_id=correlation_id,
                    user=user,
                    link=link,
                    actor_id=actor.id,
                    group_id=group_id,
                )


def provision_verified_identity(
    identity: VerifiedIdentity,
    policy: dict[str, Any],
    *,
    correlation_id: str,
    attempt_generation: int,
) -> ProvisioningResult:
    """Apply one verified snapshot atomically and emit durable safe failures."""

    try:
        identity.validate_for(
            provider_id=policy.get("id", ""),
            source_id=(policy.get("sourceBinding") or {}).get("sourceId", ""),
        )
    except Exception as exc:
        _security_event(exc, identity=identity, correlation_id=correlation_id)
        raise

    if policy.get("principalProvisioning") == "restricted" and not _eligible(
        identity, policy
    ):
        error = EligibilityError("identity does not satisfy restricted policy")
        try:
            with transaction.atomic():
                _source_binding(identity, policy)
                link = (
                    ExternalIdentityLink.objects.select_for_update()
                    .filter(
                        provider_id=identity.provider_id,
                        source_id=identity.source_id,
                        external_subject=identity.subject,
                    )
                    .first()
                )
                if link is not None and link.revoked_at is None:
                    now = timezone.now()
                    link.revoked_at = now
                    link.revocation_generation += 1
                    link.save(
                        update_fields=("revoked_at", "revocation_generation")
                    )
                    GroupMembershipGrant.objects.filter(
                        identity_link=link
                    ).update(revoked_at=now)
        except Exception as exc:
            _security_event(
                exc, identity=identity, correlation_id=correlation_id
            )
            raise
        _security_event(error, identity=identity, correlation_id=correlation_id)
        raise error

    try:
        with transaction.atomic():
            _source_binding(identity, policy)
            user, link, _created = _principal_and_link(
                identity, policy, correlation_id=correlation_id
            )
            # Serialize every update for this Principal/link and reject older
            # provider snapshots finishing after a newer accepted attempt.
            user = get_user_model().objects.select_for_update().get(pk=user.pk)
            link = ExternalIdentityLink.objects.select_for_update().get(
                pk=link.pk
            )
            if attempt_generation <= link.last_applied_generation:
                raise StaleAuthenticationAttemptError(
                    "stale authentication attempt"
                )
            _apply_profile(
                user, identity, policy, correlation_id=correlation_id, link=link
            )
            actor = _actor(
                user, identity, policy, correlation_id=correlation_id
            )
            _reconcile_groups(
                user,
                link,
                actor,
                identity,
                policy,
                correlation_id=correlation_id,
            )
            link.last_applied_generation = attempt_generation
            link.save(update_fields=("last_applied_generation",))
            return ProvisioningResult(
                user=user,
                identity_link=link,
                actor_id=actor.id if actor is not None else None,
            )
    except Exception as exc:
        _security_event(exc, identity=identity, correlation_id=correlation_id)
        raise
