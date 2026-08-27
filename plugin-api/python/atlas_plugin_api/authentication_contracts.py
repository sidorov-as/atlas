"""Reusable conformance tests for ``atlas.auth.providers.v1`` providers.

The helpers in this module intentionally do not import pytest or Atlas Core.
Provider packages supply factories and state snapshots, then call the relevant
``run_*_provider_contract`` function from their own test runner.

These checks verify cooperative conformance by trusted server plugins.  They
are not a sandbox and cannot make malicious Python code safe.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier
from typing import cast

from .authentication import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    AuthenticationFlowKind,
    AuthenticationProviderDescriptor,
    CredentialAuthenticationProvider,
    CredentialFieldKind,
    CredentialFlowContext,
    CredentialInput,
    RedirectAuthenticationProvider,
    RedirectCallbackContext,
    RedirectChallenge,
    RedirectFlowContext,
    VerifiedIdentity,
)


class AuthenticationProviderContractError(AssertionError):
    """A provider or fixture violated the public authentication contract."""


@dataclass(frozen=True, slots=True)
class AuthenticationResultLimits:
    """Bounds applied by the contract kit to normalized provider results."""

    max_subject_length: int = 1024
    max_profile_value_length: int = 4096
    max_attributes: int = 64
    max_attribute_value_length: int = 4096
    max_groups: int = 2048
    max_group_length: int = 1024

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


DEFAULT_AUTHENTICATION_RESULT_LIMITS = AuthenticationResultLimits()


type StateSnapshot = object
type StateProbe = Callable[[], StateSnapshot]


def _no_state() -> None:
    return None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuthenticationProviderContractError(message)


def _invoke_provider[Result](operation: Callable[[], Result], *, phase: str) -> Result:
    try:
        return operation()
    except Exception:  # noqa: BLE001 - provider code must be contained
        raise AuthenticationProviderContractError(
            f"provider raised during {phase}; it must return a safe contract value"
        ) from None


def _assert_unchanged(
    before: StateSnapshot,
    after: StateSnapshot,
    *,
    boundary: str,
) -> None:
    _require(
        before == after,
        f"provider changed Core-owned {boundary}; providers may only return results",
    )


def _secret_occurs(value: object, secrets: Sequence[str]) -> bool:
    """Inspect a persistence snapshot without stringifying it."""

    if isinstance(value, str):
        return any(secret and secret in value for secret in secrets)
    if isinstance(value, Mapping):
        return any(
            _secret_occurs(key, secrets) or _secret_occurs(item, secrets)
            for key, item in value.items()
        )
    if isinstance(value, (tuple, list, set, frozenset)):
        return any(_secret_occurs(item, secrets) for item in value)
    return False


def assert_safe_failure(
    result: object,
    *,
    expected_category: AuthenticationFailureCategory | None = None,
    forbidden_values: Sequence[str] = (),
) -> AuthenticationFailure:
    """Require the allowlisted failure value and check its representation."""

    _require(
        type(result) is AuthenticationFailure,
        "provider failures must use the exact AuthenticationFailure value type",
    )
    failure = cast(AuthenticationFailure, result)
    if expected_category is not None:
        _require(
            failure.category is expected_category,
            f"expected {expected_category.value!r} failure, got "
            f"{failure.category.value!r}",
        )
    rendered = repr(failure)
    for value in forbidden_values:
        _require(
            not value or value not in rendered,
            "authentication failure representation disclosed sensitive input",
        )
    return failure


def assert_valid_identity(
    result: object,
    *,
    provider_id: str,
    source_id: str,
    limits: AuthenticationResultLimits = DEFAULT_AUTHENTICATION_RESULT_LIMITS,
) -> VerifiedIdentity:
    """Validate a provider result before Core provisioning is allowed."""

    _require(
        type(result) is VerifiedIdentity,
        "successful results must use the exact VerifiedIdentity value type; "
        "authorization-bearing wrappers are forbidden",
    )
    identity = cast(VerifiedIdentity, result)
    identity.validate_for(provider_id=provider_id, source_id=source_id)
    _require(
        len(identity.subject) <= limits.max_subject_length,
        "verified identity subject exceeds the configured result limit",
    )
    for value in (
        identity.profile.username,
        identity.profile.display_name,
        identity.profile.email,
    ):
        if value is not None:
            _require(
                len(value) <= limits.max_profile_value_length,
                "verified identity profile value exceeds the configured result limit",
            )
    _require(
        len(identity.attributes) <= limits.max_attributes,
        "verified identity has too many attributes",
    )
    for name, attribute in identity.attributes.items():
        _require(
            len(name) <= limits.max_profile_value_length
            and len(attribute.value) <= limits.max_attribute_value_length,
            "verified identity attribute exceeds the configured result limit",
        )
    _require(
        len(identity.groups.groups) <= limits.max_groups,
        "verified identity has too many external groups",
    )
    for group in identity.groups.groups:
        _require(
            len(group) <= limits.max_group_length,
            "external group exceeds the configured result limit",
        )
    return identity


@dataclass(frozen=True, slots=True)
class CredentialProviderContractHooks:
    """Provider-owned factories used by the reusable credential suite.

    ``state_probe`` snapshots Core session/authorization state and
    ``persistence_probe`` snapshots storage that could accidentally retain
    credentials.  Their returned values must support equality.  The contract
    runner never needs a Django model, session object, or repository fixture.
    """

    provider_factory: Callable[[], CredentialAuthenticationProvider]
    context_factory: Callable[[], CredentialFlowContext]
    valid_credentials_factory: Callable[[], CredentialInput]
    invalid_credentials_factory: Callable[[], CredentialInput]
    unavailable_credentials_factory: Callable[[], CredentialInput]
    state_probe: StateProbe = _no_state
    persistence_probe: StateProbe = _no_state
    limits: AuthenticationResultLimits = AuthenticationResultLimits()


@dataclass(frozen=True, slots=True)
class RedirectProviderContractHooks:
    """Provider-owned factories used by the reusable redirect suite.

    Each callback factory receives the start challenge.  It must construct a
    callback for the named browser/protocol condition.  Providers must consume
    successful state atomically; invalid callbacks must return a safe failure.
    """

    provider_factory: Callable[[], RedirectAuthenticationProvider]
    start_context_factory: Callable[[], RedirectFlowContext]
    valid_callback_factory: Callable[[RedirectChallenge], RedirectCallbackContext]
    mismatched_callback_factory: Callable[[RedirectChallenge], RedirectCallbackContext]
    expired_callback_factory: Callable[[RedirectChallenge], RedirectCallbackContext]
    browser_mismatched_callback_factory: Callable[
        [RedirectChallenge], RedirectCallbackContext
    ]
    unavailable_callback_factory: Callable[[RedirectChallenge], RedirectCallbackContext]
    state_probe: StateProbe = _no_state
    limits: AuthenticationResultLimits = AuthenticationResultLimits()


def _assert_descriptor(
    descriptor: object,
    *,
    flow_kind: AuthenticationFlowKind,
) -> AuthenticationProviderDescriptor:
    _require(
        type(descriptor) is AuthenticationProviderDescriptor,
        "provider descriptor must use AuthenticationProviderDescriptor",
    )
    descriptor = cast(AuthenticationProviderDescriptor, descriptor)
    _require(
        descriptor.flow_kind is flow_kind,
        f"provider descriptor must declare flow_kind={flow_kind.value!r}",
    )
    return descriptor


def run_credential_provider_contract(
    hooks: CredentialProviderContractHooks,
) -> None:
    """Run the mandatory provider-independent credential conformance suite."""

    provider = hooks.provider_factory()
    descriptor = _assert_descriptor(
        provider.descriptor, flow_kind=AuthenticationFlowKind.CREDENTIALS
    )
    context = hooks.context_factory()
    _require(
        context.provider_id == descriptor.id,
        "credential context provider id must match the descriptor",
    )

    credentials = hooks.valid_credentials_factory()
    secret_field_ids = {
        field.id
        for field in descriptor.presentation.credential_fields
        if field.kind is CredentialFieldKind.SECRET
    }
    secrets = tuple(
        value
        for field_id, value in credentials.values.items()
        if field_id in secret_field_ids
    )
    before_state = hooks.state_probe()
    before_persistence = hooks.persistence_probe()
    first = assert_valid_identity(
        _invoke_provider(
            lambda: provider.authenticate(context, credentials),
            phase="credential authentication",
        ),
        provider_id=descriptor.id,
        source_id=context.source_id,
        limits=hooks.limits,
    )
    second = assert_valid_identity(
        _invoke_provider(
            lambda: provider.authenticate(
                hooks.context_factory(), hooks.valid_credentials_factory()
            ),
            phase="repeated credential authentication",
        ),
        provider_id=descriptor.id,
        source_id=context.source_id,
        limits=hooks.limits,
    )
    _require(
        first.subject == second.subject,
        "the same verified account must return a stable subject",
    )
    _assert_unchanged(
        before_state,
        hooks.state_probe(),
        boundary="session/authorization state",
    )
    invalid = hooks.invalid_credentials_factory()
    assert_safe_failure(
        _invoke_provider(
            lambda: provider.authenticate(hooks.context_factory(), invalid),
            phase="invalid credential authentication",
        ),
        expected_category=AuthenticationFailureCategory.INVALID_CREDENTIALS,
        forbidden_values=tuple(
            value
            for field_id, value in invalid.values.items()
            if field_id in secret_field_ids
        ),
    )
    unavailable = hooks.unavailable_credentials_factory()
    assert_safe_failure(
        _invoke_provider(
            lambda: provider.authenticate(hooks.context_factory(), unavailable),
            phase="unavailable credential authentication",
        ),
        expected_category=AuthenticationFailureCategory.UNAVAILABLE,
        forbidden_values=tuple(
            value
            for field_id, value in unavailable.values.items()
            if field_id in secret_field_ids
        ),
    )
    all_secrets = secrets + tuple(
        value
        for credential_input in (invalid, unavailable)
        for field_id, value in credential_input.values.items()
        if field_id in secret_field_ids
    )
    after_persistence = hooks.persistence_probe()
    _require(
        not _secret_occurs(after_persistence, all_secrets),
        "provider persisted submitted credential values",
    )
    _require(
        before_persistence == after_persistence,
        "provider changed persistence while verifying credentials",
    )
    _assert_unchanged(
        before_state,
        hooks.state_probe(),
        boundary="session/authorization state",
    )


def _start_redirect(
    hooks: RedirectProviderContractHooks,
    provider: RedirectAuthenticationProvider,
) -> tuple[
    AuthenticationProviderDescriptor,
    RedirectFlowContext,
    RedirectChallenge,
]:
    descriptor = _assert_descriptor(
        provider.descriptor, flow_kind=AuthenticationFlowKind.REDIRECT
    )
    context = hooks.start_context_factory()
    _require(
        context.provider_id == descriptor.id,
        "redirect context provider id must match the descriptor",
    )
    challenge = _invoke_provider(
        lambda: provider.begin(context), phase="redirect start"
    )
    _require(
        type(challenge) is RedirectChallenge,
        "redirect begin must return the exact RedirectChallenge value type",
    )
    return descriptor, context, challenge


def _assert_callback_correlation(
    callback: RedirectCallbackContext,
    *,
    descriptor: AuthenticationProviderDescriptor,
    start_context: RedirectFlowContext,
) -> None:
    _require(
        callback.provider_id == descriptor.id,
        "redirect callback provider id must match the descriptor",
    )
    _require(
        callback.source_id == start_context.source_id,
        "redirect callback source id must match the start context",
    )


def _run_rejected_callback(
    hooks: RedirectProviderContractHooks,
    callback_factory: Callable[[RedirectChallenge], RedirectCallbackContext],
) -> None:
    provider = hooks.provider_factory()
    _, _, challenge = _start_redirect(hooks, provider)
    assert_safe_failure(
        _invoke_provider(
            lambda: provider.complete(callback_factory(challenge)),
            phase="rejected redirect callback",
        )
    )


def run_redirect_provider_contract(
    hooks: RedirectProviderContractHooks,
) -> None:
    """Run the mandatory provider-independent redirect conformance suite."""

    before_state = hooks.state_probe()
    provider = hooks.provider_factory()
    descriptor, start_context, challenge = _start_redirect(hooks, provider)
    callback = hooks.valid_callback_factory(challenge)
    _assert_callback_correlation(
        callback, descriptor=descriptor, start_context=start_context
    )
    first = assert_valid_identity(
        _invoke_provider(
            lambda: provider.complete(callback), phase="redirect callback"
        ),
        provider_id=descriptor.id,
        source_id=callback.source_id,
        limits=hooks.limits,
    )
    replay = _invoke_provider(
        lambda: provider.complete(callback), phase="replayed redirect callback"
    )
    assert_safe_failure(replay)
    _assert_unchanged(
        before_state,
        hooks.state_probe(),
        boundary="session/authorization state",
    )

    provider_again = hooks.provider_factory()
    descriptor_again, start_context_again, challenge_again = _start_redirect(
        hooks, provider_again
    )
    callback_again = hooks.valid_callback_factory(challenge_again)
    _assert_callback_correlation(
        callback_again,
        descriptor=descriptor_again,
        start_context=start_context_again,
    )
    second = assert_valid_identity(
        _invoke_provider(
            lambda: provider_again.complete(callback_again),
            phase="repeated redirect callback",
        ),
        provider_id=descriptor_again.id,
        source_id=callback_again.source_id,
        limits=hooks.limits,
    )
    _require(
        first.subject == second.subject,
        "the same verified redirect account must return a stable subject",
    )

    _run_rejected_callback(hooks, hooks.mismatched_callback_factory)
    _run_rejected_callback(hooks, hooks.expired_callback_factory)
    _run_rejected_callback(hooks, hooks.browser_mismatched_callback_factory)

    unavailable_provider = hooks.provider_factory()
    _, _, unavailable_challenge = _start_redirect(hooks, unavailable_provider)
    assert_safe_failure(
        _invoke_provider(
            lambda: unavailable_provider.complete(
                hooks.unavailable_callback_factory(unavailable_challenge)
            ),
            phase="unavailable redirect callback",
        ),
        expected_category=AuthenticationFailureCategory.UNAVAILABLE,
    )

    concurrent_provider = hooks.provider_factory()
    (
        concurrent_descriptor,
        concurrent_start,
        concurrent_challenge,
    ) = _start_redirect(hooks, concurrent_provider)
    concurrent_callback = hooks.valid_callback_factory(concurrent_challenge)
    _assert_callback_correlation(
        concurrent_callback,
        descriptor=concurrent_descriptor,
        start_context=concurrent_start,
    )
    callback_barrier = Barrier(2)

    def complete_concurrently() -> VerifiedIdentity | AuthenticationFailure:
        callback_barrier.wait()
        return _invoke_provider(
            lambda: concurrent_provider.complete(concurrent_callback),
            phase="simultaneous redirect callback",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(lambda _: complete_concurrently(), range(2)))
    successes = [result for result in results if type(result) is VerifiedIdentity]
    failures = [result for result in results if type(result) is AuthenticationFailure]
    _require(
        len(successes) == 1 and len(failures) == 1,
        "redirect state must be consumed atomically by at most one callback",
    )
    assert_valid_identity(
        successes[0],
        provider_id=concurrent_descriptor.id,
        source_id=concurrent_callback.source_id,
        limits=hooks.limits,
    )
    _assert_unchanged(
        before_state,
        hooks.state_probe(),
        boundary="session/authorization state",
    )


__all__ = [
    "AuthenticationProviderContractError",
    "AuthenticationResultLimits",
    "CredentialProviderContractHooks",
    "RedirectProviderContractHooks",
    "assert_safe_failure",
    "assert_valid_identity",
    "run_credential_provider_contract",
    "run_redirect_provider_contract",
]
