"""Tests for the publishable authentication provider contract-test kit."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Lock

import pytest

from atlas_plugin_api import (
    AssuredAttribute,
    AttributeProvenance,
    AuthenticationFailure,
    AuthenticationFailureCategory,
    AuthenticationFlowKind,
    AuthenticationProviderContractError,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    AuthenticationResultLimits,
    CredentialFieldKind,
    CredentialFieldPresentation,
    CredentialFlowContext,
    CredentialInput,
    CredentialProviderContractHooks,
    ExternalGroupSnapshot,
    ExternalProfile,
    InvalidAuthenticationResultError,
    RedirectCallbackContext,
    RedirectChallenge,
    RedirectFlowContext,
    RedirectProviderContractHooks,
    VerifiedIdentity,
    assert_safe_failure,
    assert_valid_identity,
    run_credential_provider_contract,
    run_redirect_provider_contract,
)

PROVIDER_ID = "example.auth.fixture"
SOURCE_ID = "urn:atlas:test-directory"


def _deadline() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=1)


def _credential_context() -> CredentialFlowContext:
    return CredentialFlowContext(
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        attempt_id="attempt-credential",
        correlation_id="correlation-credential",
        deadline=_deadline(),
    )


def _identity(*, groups: ExternalGroupSnapshot | None = None) -> VerifiedIdentity:
    return VerifiedIdentity(
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        subject="person-42",
        profile=ExternalProfile(
            username="person",
            display_name="Example Person",
            email="person@example.com",
        ),
        attributes={
            "email": AssuredAttribute(
                "person@example.com", AttributeProvenance.VERIFIED_OWNERSHIP
            ),
            "department": AssuredAttribute(
                "engineering", AttributeProvenance.SELF_ASSERTED
            ),
        },
        groups=groups or ExternalGroupSnapshot.complete(),
    )


class _CredentialProvider:
    descriptor = AuthenticationProviderDescriptor(
        id=PROVIDER_ID,
        flow_kind=AuthenticationFlowKind.CREDENTIALS,
        presentation=AuthenticationProviderPresentation(
            display_name="Fixture credentials",
            credential_fields=(
                CredentialFieldPresentation(
                    id="username",
                    label="Username",
                    kind=CredentialFieldKind.TEXT,
                ),
                CredentialFieldPresentation(
                    id="password",
                    label="Password",
                    kind=CredentialFieldKind.SECRET,
                ),
            ),
        ),
    )

    def authenticate(self, context, credentials):
        if credentials.values["username"] == "outage":
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE, retryable=True
            )
        if credentials.values != {"username": "person", "password": "correct"}:
            return AuthenticationFailure(
                AuthenticationFailureCategory.INVALID_CREDENTIALS
            )
        return _identity()


def _credential_hooks() -> CredentialProviderContractHooks:
    stored_rows: list[object] = []
    core_state = {"session": None, "permissions": ()}
    return CredentialProviderContractHooks(
        provider_factory=_CredentialProvider,
        context_factory=_credential_context,
        valid_credentials_factory=lambda: CredentialInput(
            {"username": "person", "password": "correct"}
        ),
        invalid_credentials_factory=lambda: CredentialInput(
            {"username": "person", "password": "wrong-secret"}
        ),
        unavailable_credentials_factory=lambda: CredentialInput(
            {"username": "outage", "password": "outage-secret"}
        ),
        state_probe=lambda: dict(core_state),
        persistence_probe=lambda: tuple(stored_rows),
    )


class _RedirectProvider:
    descriptor = AuthenticationProviderDescriptor(
        id=PROVIDER_ID,
        flow_kind=AuthenticationFlowKind.REDIRECT,
        presentation=AuthenticationProviderPresentation(display_name="Fixture SSO"),
    )

    def __init__(self) -> None:
        self._lock = Lock()
        self._consumed = False

    def begin(self, context):
        self._consumed = False
        return RedirectChallenge("https://idp.example/authorize?state=good-state")

    def complete(self, context):
        parameters = context.callback_parameters
        if parameters.get("outcome") == "outage":
            return AuthenticationFailure(
                AuthenticationFailureCategory.UNAVAILABLE, retryable=True
            )
        if (
            parameters.get("state") != "good-state"
            or parameters.get("browser") != "browser-a"
            or parameters.get("expired") == "true"
        ):
            return AuthenticationFailure(AuthenticationFailureCategory.INVALID_RESULT)
        with self._lock:
            if self._consumed:
                return AuthenticationFailure(
                    AuthenticationFailureCategory.INVALID_RESULT
                )
            self._consumed = True
        return _identity(groups=ExternalGroupSnapshot.complete(("engineering",)))


def _redirect_context() -> RedirectFlowContext:
    return RedirectFlowContext(
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        attempt_id="attempt-redirect",
        correlation_id="correlation-redirect",
        deadline=_deadline(),
        callback_url="https://atlas.example/auth/browser/v1/callback",
    )


def _callback(**parameters: str) -> RedirectCallbackContext:
    return RedirectCallbackContext(
        provider_id=PROVIDER_ID,
        source_id=SOURCE_ID,
        attempt_id="attempt-redirect",
        correlation_id="correlation-redirect",
        deadline=_deadline(),
        callback_parameters=parameters,
    )


def _redirect_hooks() -> RedirectProviderContractHooks:
    core_state = {"session_key": "pre-login-session", "permissions": ()}
    return RedirectProviderContractHooks(
        provider_factory=_RedirectProvider,
        start_context_factory=_redirect_context,
        valid_callback_factory=lambda challenge: _callback(
            state="good-state", browser="browser-a"
        ),
        mismatched_callback_factory=lambda challenge: _callback(
            state="wrong-state", browser="browser-a"
        ),
        expired_callback_factory=lambda challenge: _callback(
            state="good-state", browser="browser-a", expired="true"
        ),
        browser_mismatched_callback_factory=lambda challenge: _callback(
            state="good-state", browser="browser-b"
        ),
        unavailable_callback_factory=lambda challenge: _callback(
            state="good-state", browser="browser-a", outcome="outage"
        ),
        state_probe=lambda: dict(core_state),
    )


def test_public_credential_contract_suite_passes_for_independent_fixture():
    run_credential_provider_contract(_credential_hooks())


def test_public_redirect_contract_suite_covers_replay_and_correlation():
    run_redirect_provider_contract(_redirect_hooks())


def test_common_contract_rejects_provider_owned_session_establishment():
    core_state = {"session": None, "permissions": ()}

    class SessionCreatingProvider(_CredentialProvider):
        def authenticate(self, context, credentials):
            result = super().authenticate(context, credentials)
            if type(result) is VerifiedIdentity:
                core_state["session"] = "provider-created-session"
            return result

    hooks = replace(
        _credential_hooks(),
        provider_factory=SessionCreatingProvider,
        state_probe=lambda: dict(core_state),
    )

    with pytest.raises(AuthenticationProviderContractError, match="Core-owned"):
        run_credential_provider_contract(hooks)


def test_common_contract_rejects_invalid_flow_metadata():
    class WrongFlowProvider(_CredentialProvider):
        descriptor = AuthenticationProviderDescriptor(
            id=PROVIDER_ID,
            flow_kind=AuthenticationFlowKind.REDIRECT,
            presentation=AuthenticationProviderPresentation(display_name="Wrong flow"),
        )

    hooks = replace(_credential_hooks(), provider_factory=WrongFlowProvider)

    with pytest.raises(AuthenticationProviderContractError, match="credentials"):
        run_credential_provider_contract(hooks)


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (object(), "exact VerifiedIdentity"),
        (
            type(
                "AuthorizationBearingResult",
                (),
                {"identity": _identity(), "permissions": ("catalog.admin",)},
            )(),
            "authorization-bearing",
        ),
    ],
)
def test_common_contract_rejects_missing_or_authorization_bearing_results(
    result, message
):
    with pytest.raises(AuthenticationProviderContractError, match=message):
        assert_valid_identity(result, provider_id=PROVIDER_ID, source_id=SOURCE_ID)


def test_common_contract_rejects_provider_and_source_mismatch():
    with pytest.raises(InvalidAuthenticationResultError, match="provider_id"):
        assert_valid_identity(
            _identity(), provider_id="example.auth.other", source_id=SOURCE_ID
        )
    with pytest.raises(InvalidAuthenticationResultError, match="source"):
        assert_valid_identity(
            _identity(), provider_id=PROVIDER_ID, source_id="urn:atlas:other"
        )


def test_common_contract_preserves_provenance_and_complete_empty_groups():
    identity = assert_valid_identity(
        _identity(), provider_id=PROVIDER_ID, source_id=SOURCE_ID
    )

    assert (
        identity.attributes["department"].provenance
        is AttributeProvenance.SELF_ASSERTED
    )
    assert identity.groups == ExternalGroupSnapshot.complete()


def test_common_contract_rejects_partial_group_objects_and_oversized_results():
    partial = type("PartialGroups", (), {"groups": ("engineering",)})()
    with pytest.raises(TypeError, match="groups must be ExternalGroupSnapshot"):
        VerifiedIdentity(
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            subject="person-42",
            groups=partial,
        )

    with pytest.raises(AuthenticationProviderContractError, match="too many external"):
        assert_valid_identity(
            _identity(groups=ExternalGroupSnapshot.complete(("one", "two"))),
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            limits=AuthenticationResultLimits(max_groups=1),
        )


def test_empty_credentials_and_empty_subject_are_rejected_before_provider_use():
    with pytest.raises(ValueError, match="must not be empty"):
        CredentialInput({})
    with pytest.raises(ValueError, match="subject"):
        VerifiedIdentity(
            provider_id=PROVIDER_ID,
            source_id=SOURCE_ID,
            subject="",
        )


def test_failure_contract_rejects_exception_objects_and_secret_details():
    with pytest.raises(AuthenticationProviderContractError, match="exact"):
        assert_safe_failure(RuntimeError("password=secret"))


def test_credential_suite_sanitizes_provider_exceptions():
    class RaisingProvider(_CredentialProvider):
        def authenticate(self, context, credentials):
            raise RuntimeError("upstream body contains super-secret")

    hooks = replace(_credential_hooks(), provider_factory=RaisingProvider)

    with pytest.raises(AuthenticationProviderContractError) as exc_info:
        run_credential_provider_contract(hooks)

    assert "super-secret" not in str(exc_info.value)


def test_contract_failure_from_one_provider_does_not_poison_another_instance():
    failing = _CredentialProvider().authenticate(
        _credential_context(),
        CredentialInput({"username": "outage", "password": "x"}),
    )
    healthy = _CredentialProvider().authenticate(
        _credential_context(),
        CredentialInput({"username": "person", "password": "correct"}),
    )

    assert_safe_failure(
        failing, expected_category=AuthenticationFailureCategory.UNAVAILABLE
    )
    assert_valid_identity(healthy, provider_id=PROVIDER_ID, source_id=SOURCE_ID)
