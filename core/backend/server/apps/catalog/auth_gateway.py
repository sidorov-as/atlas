"""Core-owned browser authentication gateway."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta
from typing import Any, cast
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlsplit
from uuid import UUID, uuid4

from allauth.headless.account.views import SignupView
from allauth.headless.constants import Client
from atlas_plugin_api import (
    AuthenticationFailure,
    AuthenticationFailureCategory,
    AuthenticationFlowKind,
    CredentialAuthenticationProvider,
    CredentialFlowContext,
    CredentialInput,
    InvalidAuthenticationResultError,
    RedirectAuthenticationProvider,
    RedirectCallbackContext,
    RedirectFlowContext,
    VerifiedIdentity,
    get_authentication_provider_lookup,
)
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .auth_policy import (
    LOCAL_PROVIDER_ID,
    authentication_policy,
    provider_source_id,
    public_authentication_config,
    selected_provider,
)
from .auth_security import (
    MAX_AUTH_REQUEST_BYTES,
    MAX_CALLBACK_FIELDS,
    MAX_CALLBACK_VALUE_BYTES,
    authentication_budget_allowed,
    current_policy_generation,
    source_binding_generation,
)
from .models import AuthenticationAttempt
from .provisioning import provision_verified_identity

log = logging.getLogger(__name__)

_ATTEMPT_LIFETIME = timedelta(minutes=10)
_AUTHENTICATION_BACKEND = (
    "server.apps.catalog.auth_backends.AtlasAllauthAuthenticationBackend"
)


def _request_data(request: HttpRequest) -> dict[str, Any]:
    try:
        content_length = int(request.META.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        return {}
    if content_length > MAX_AUTH_REQUEST_BYTES:
        return {}
    if request.content_type == "application/json":
        try:
            body = request.body
            if len(body) > MAX_AUTH_REQUEST_BYTES:
                return {}
            value = json.loads(body or b"{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            return {}
        return value if isinstance(value, dict) else {}
    return request.POST.dict()


def _error(
    category: str,
    *,
    stage: str,
    status: int,
    correlation_id: UUID | str | None = None,
    retryable: bool = False,
) -> JsonResponse:
    response = JsonResponse(
        {
            "error": {
                "category": category,
                "stage": stage,
                "correlationId": str(correlation_id or uuid4()),
                "retryable": retryable,
            }
        },
        status=status,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _selected_for_flow(
    provider_id: str, flow_kind: AuthenticationFlowKind, *, stage: str
) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    provider = selected_provider(provider_id)
    if provider is None:
        return None, _error("provider_not_available", stage=stage, status=404)
    if provider.get("flowKind") != flow_kind.value:
        return None, _error("wrong_flow", stage=stage, status=404)
    return provider, None


def _source_id(provider: dict[str, Any]) -> str | None:
    return provider_source_id(provider)


def _provider_failure(
    failure: AuthenticationFailure,
    *,
    stage: str,
    correlation_id: UUID,
) -> JsonResponse:
    category = {
        AuthenticationFailureCategory.INVALID_CREDENTIALS: (
            "invalid_credentials",
            400,
        ),
        AuthenticationFailureCategory.UNAVAILABLE: (
            "provider_unavailable",
            503,
        ),
        AuthenticationFailureCategory.INVALID_RESULT: ("invalid_result", 400),
        AuthenticationFailureCategory.CANCELED: ("canceled", 400),
    }[failure.category]
    return _error(
        category[0],
        stage=stage,
        status=category[1],
        correlation_id=correlation_id,
        retryable=failure.retryable,
    )


def _callback_error(
    request: HttpRequest,
    category: str,
    *,
    status: int,
    correlation_id: UUID | str | None = None,
    retryable: bool = False,
    return_url: str | None = None,
) -> HttpResponse:
    """Return JSON to API callers and safe fallback UX to browsers."""

    safe_correlation_id = str(correlation_id or uuid4())
    if "text/html" in request.headers.get("Accept", ""):
        query = {
            "choose-provider": "1",
            "auth-error": category,
            "correlation-id": safe_correlation_id,
        }
        if return_url is not None:
            query["return-url"] = return_url
        location = "/login?" + urlencode(query)
        return HttpResponse(
            status=302,
            headers={"Location": location, "Cache-Control": "no-store"},
        )
    return _error(
        category,
        stage="redirect_callback",
        status=status,
        correlation_id=safe_correlation_id,
        retryable=retryable,
    )


def _callback_provider_failure(
    request: HttpRequest,
    failure: AuthenticationFailure,
    *,
    correlation_id: UUID,
    return_url: str,
) -> HttpResponse:
    category, status = {
        AuthenticationFailureCategory.INVALID_CREDENTIALS: (
            "invalid_credentials",
            400,
        ),
        AuthenticationFailureCategory.UNAVAILABLE: (
            "provider_unavailable",
            503,
        ),
        AuthenticationFailureCategory.INVALID_RESULT: ("invalid_result", 400),
        AuthenticationFailureCategory.CANCELED: ("canceled", 400),
    }[failure.category]
    return _callback_error(
        request,
        category,
        status=status,
        correlation_id=correlation_id,
        retryable=failure.retryable,
        return_url=return_url,
    )


def _establish_session(
    request: HttpRequest,
    *,
    user,
    provider_id: str,
    source_id: str | None = None,
    identity_link=None,
) -> None:
    setattr(request, "_atlas_auth_provider", provider_id)
    setattr(request, "_atlas_auth_source", source_id)
    setattr(request, "_atlas_auth_identity_link", identity_link)
    login(request, user, backend=_AUTHENTICATION_BACKEND)


def _rate_limit(request: HttpRequest, *, provider_id: str, account: str = ""):
    allowed, retry_after = authentication_budget_allowed(
        request, provider_id=provider_id, account=account
    )
    if allowed:
        return None
    response = _error(
        "rate_limited", stage="authentication", status=429, retryable=True
    )
    response.headers["Retry-After"] = str(retry_after)
    return response


def _session_payload(request: HttpRequest) -> dict[str, Any]:
    if not request.user.is_authenticated:
        return {"data": {"user": None}, "meta": {"is_authenticated": False}}
    username = request.user.get_username()
    display = request.user.get_full_name() or username
    return {
        "data": {
            "user": {
                "id": request.user.pk,
                "display": display,
                "username": username,
            }
        },
        "meta": {"is_authenticated": True},
    }


def _browser_session_digest(request: HttpRequest) -> str:
    if request.session.session_key is None:
        request.session.create()
    session_key = request.session.session_key
    if session_key is None:  # pragma: no cover - backend contract violation
        raise RuntimeError("session backend did not allocate a session key")
    return hashlib.sha256(session_key.encode()).hexdigest()


def _state_digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _safe_return_url(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return "/"
    if "\\" in value or any(ord(character) < 32 for character in value):
        return None
    decoded = unquote(value)
    if unquote(decoded) != decoded:
        return None
    public_origin = authentication_policy().get("publicOrigin")
    if not isinstance(public_origin, str) or not public_origin:
        return None
    origin = urlsplit(public_origin)
    candidate = urlsplit(decoded)
    if candidate.username or candidate.password or candidate.fragment:
        return None
    if candidate.scheme or candidate.netloc:
        candidate_origin = (candidate.scheme, candidate.netloc)
        if candidate_origin != (origin.scheme, origin.netloc):
            return None
        path = candidate.path or "/"
        return path + (f"?{candidate.query}" if candidate.query else "")
    if not candidate.path.startswith("/") or candidate.path.startswith("//"):
        return None
    return candidate.path + (f"?{candidate.query}" if candidate.query else "")


def _callback_url(provider_id: str) -> str:
    origin = authentication_policy().get("publicOrigin", "")
    path = reverse(
        "atlas-auth-provider-callback",
        kwargs={"provider_id": provider_id},
    )
    return urljoin(origin.rstrip("/") + "/", path.lstrip("/"))


def _logout_return_url() -> str:
    origin = authentication_policy().get("publicOrigin", "")
    return urljoin(origin.rstrip("/") + "/", "login?logged-out=1")


def _authorization_state(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password or parsed.fragment:
        return None
    if parsed.scheme == "http":
        trust = authentication_policy().get("outboundTrust", {})
        if not (settings.DEBUG and trust.get("allowDevelopmentHttp") is True):
            return None
    values = parse_qs(parsed.query, keep_blank_values=True).get("state", ())
    return values[0] if len(values) == 1 and values[0] else None


@never_cache
@ensure_csrf_cookie
@require_GET
def authentication_config(request: HttpRequest) -> JsonResponse:
    get_token(request)
    return JsonResponse(public_authentication_config())


@never_cache
@ensure_csrf_cookie
def authentication_session(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        get_token(request)
        return JsonResponse(_session_payload(request))
    if request.method == "DELETE":
        provider_id = request.session.get("atlas_auth_provider")
        runtime = (
            get_authentication_provider_lookup().get(provider_id)
            if isinstance(provider_id, str)
            else None
        )
        logout(request)
        remote_logout = getattr(runtime, "remote_logout", None)
        if callable(remote_logout):
            try:
                target = remote_logout(_logout_return_url())
            except Exception:
                log.warning(
                    "authentication_remote_logout_failed",
                    extra={"provider_id": provider_id},
                )
            else:
                if isinstance(target, str) and target:
                    return JsonResponse(
                        {"remoteLogoutUrl": target},
                        headers={"Cache-Control": "no-store"},
                    )
        return HttpResponse(status=204, headers={"Cache-Control": "no-store"})
    return HttpResponse(status=405, headers={"Allow": "GET, DELETE"})


@never_cache
@require_POST
def provider_credentials(
    request: HttpRequest, provider_id: str
) -> JsonResponse:
    correlation_id = uuid4()
    provider_policy, error = _selected_for_flow(
        provider_id, AuthenticationFlowKind.CREDENTIALS, stage="credentials"
    )
    if error is not None:
        return error
    assert provider_policy is not None
    data = _request_data(request)
    values = data.get("credentials", data)
    if not isinstance(values, dict):
        return _error(
            "invalid_request",
            stage="credentials",
            status=400,
            correlation_id=correlation_id,
        )

    account = str(values.get("username", ""))
    limited = _rate_limit(request, provider_id=provider_id, account=account)
    if limited is not None:
        return limited

    source_id = _source_id(provider_policy)
    runtime = get_authentication_provider_lookup().get(provider_id)
    if source_id is None or runtime is None:
        return _error(
            "provider_unavailable",
            stage="credentials",
            status=503,
            correlation_id=correlation_id,
            retryable=runtime is None,
        )
    try:
        credentials = CredentialInput(values)
        now = timezone.now()
        attempt = AuthenticationAttempt.objects.create(
            provider_id=provider_id,
            source_id=source_id,
            browser_session_digest=_browser_session_digest(request),
            return_url="/",
            correlation_id=correlation_id,
            expires_at=now + _ATTEMPT_LIFETIME,
            policy_generation=current_policy_generation(),
            source_generation=source_binding_generation(provider_id, source_id),
        )
        result = cast(CredentialAuthenticationProvider, runtime).authenticate(
            CredentialFlowContext(
                provider_id=provider_id,
                source_id=source_id,
                attempt_id=str(attempt.pk),
                correlation_id=str(correlation_id),
                deadline=now + _ATTEMPT_LIFETIME,
            ),
            credentials,
        )
    except (TypeError, ValueError):
        return _error(
            "invalid_request",
            stage="credentials",
            status=400,
            correlation_id=correlation_id,
        )
    except Exception:
        log.warning(
            "authentication_provider_failed",
            extra={
                "provider_id": provider_id,
                "stage": "credentials",
                "correlation_id": str(correlation_id),
            },
        )
        return _error(
            "provider_unavailable",
            stage="credentials",
            status=503,
            correlation_id=correlation_id,
            retryable=True,
        )
    if isinstance(result, AuthenticationFailure):
        return _provider_failure(
            result, stage="credentials", correlation_id=correlation_id
        )
    if not isinstance(result, VerifiedIdentity):
        return _error(
            "invalid_result",
            stage="credentials",
            status=502,
            correlation_id=correlation_id,
        )
    try:
        result.validate_for(provider_id=provider_id, source_id=source_id)
    except InvalidAuthenticationResultError:
        return _error(
            "invalid_result",
            stage="credentials",
            status=502,
            correlation_id=correlation_id,
        )
    if (
        attempt.policy_generation != current_policy_generation()
        or attempt.source_generation
        != source_binding_generation(provider_id, source_id)
    ):
        return _error(
            "authentication_state_changed",
            stage="credentials",
            status=409,
            correlation_id=correlation_id,
            retryable=True,
        )
    if provider_id == LOCAL_PROVIDER_ID:
        user = get_user_model().objects.filter(pk=result.subject).first()
        if user is None or not user.is_active:
            return _error(
                "invalid_credentials",
                stage="credentials",
                status=400,
                correlation_id=correlation_id,
            )
        _establish_session(request, user=user, provider_id=provider_id)
        return JsonResponse(_session_payload(request))

    try:
        provisioned = provision_verified_identity(
            result,
            provider_policy,
            correlation_id=str(correlation_id),
            attempt_generation=attempt.pk,
        )
    except Exception:
        log.warning(
            "authentication_provisioning_failed",
            extra={
                "provider_id": provider_id,
                "stage": "provisioning",
                "correlation_id": str(correlation_id),
            },
        )
        return _error(
            "provisioning_failed",
            stage="provisioning",
            status=403,
            correlation_id=correlation_id,
        )
    if (
        attempt.policy_generation != current_policy_generation()
        or attempt.source_generation
        != source_binding_generation(provider_id, source_id)
    ):
        return _error(
            "authentication_state_changed",
            stage="credentials",
            status=409,
            correlation_id=correlation_id,
            retryable=True,
        )
    _establish_session(
        request,
        user=provisioned.user,
        provider_id=provider_id,
        source_id=source_id,
        identity_link=provisioned.identity_link,
    )
    return JsonResponse(_session_payload(request))


@never_cache
@require_POST
def provider_start(request: HttpRequest, provider_id: str) -> JsonResponse:
    correlation_id = uuid4()
    provider_policy, error = _selected_for_flow(
        provider_id, AuthenticationFlowKind.REDIRECT, stage="redirect_start"
    )
    if error is not None:
        return error
    assert provider_policy is not None
    limited = _rate_limit(request, provider_id=provider_id)
    if limited is not None:
        return limited
    source_id = _source_id(provider_policy)
    runtime = get_authentication_provider_lookup().get(provider_id)
    if source_id is None or runtime is None:
        return _error(
            "provider_unavailable",
            stage="redirect_start",
            status=503,
            correlation_id=correlation_id,
            retryable=runtime is None,
        )
    return_url = _safe_return_url(_request_data(request).get("returnUrl", "/"))
    if return_url is None:
        return _error(
            "unsafe_return_url",
            stage="redirect_start",
            status=400,
            correlation_id=correlation_id,
        )
    deadline = timezone.now() + _ATTEMPT_LIFETIME
    attempt = AuthenticationAttempt.objects.create(
        provider_id=provider_id,
        source_id=source_id,
        browser_session_digest=_browser_session_digest(request),
        return_url=return_url,
        correlation_id=correlation_id,
        expires_at=deadline,
        policy_generation=current_policy_generation(),
        source_generation=source_binding_generation(provider_id, source_id),
    )
    try:
        challenge = cast(RedirectAuthenticationProvider, runtime).begin(
            RedirectFlowContext(
                provider_id=provider_id,
                source_id=source_id,
                attempt_id=str(attempt.pk),
                correlation_id=str(correlation_id),
                deadline=deadline,
                callback_url=_callback_url(provider_id),
            )
        )
        state = _authorization_state(challenge.authorization_url)
        if state is None:
            raise ValueError("provider challenge has no valid state")
        attempt.state_digest = _state_digest(state)
        attempt.save(update_fields=("state_digest",))
    except Exception:
        attempt.delete()
        log.warning(
            "authentication_provider_failed",
            extra={
                "provider_id": provider_id,
                "stage": "redirect_start",
                "correlation_id": str(correlation_id),
            },
        )
        return _error(
            "provider_unavailable",
            stage="redirect_start",
            status=503,
            correlation_id=correlation_id,
            retryable=True,
        )
    return JsonResponse(
        {
            "redirectUrl": challenge.authorization_url,
            "correlationId": str(correlation_id),
        }
    )


@never_cache
@require_GET
def provider_callback(request: HttpRequest, provider_id: str) -> HttpResponse:
    provider_policy, error = _selected_for_flow(
        provider_id, AuthenticationFlowKind.REDIRECT, stage="redirect_callback"
    )
    if error is not None:
        return error
    assert provider_policy is not None
    limited = _rate_limit(request, provider_id=provider_id)
    if limited is not None:
        return limited
    if len(request.GET) > MAX_CALLBACK_FIELDS or any(
        len(value.encode()) > MAX_CALLBACK_VALUE_BYTES
        for _, values in request.GET.lists()
        for value in values
    ):
        return _callback_error(request, "invalid_request", status=400)
    state = request.GET.get("state")
    if not state:
        return _callback_error(request, "invalid_state", status=400)
    now = timezone.now()
    try:
        with transaction.atomic():
            attempt = AuthenticationAttempt.objects.select_for_update().get(
                state_digest=_state_digest(state),
                provider_id=provider_id,
            )
            invalid = (
                attempt.consumed_at is not None
                or attempt.expires_at <= now
                or attempt.browser_session_digest
                != _browser_session_digest(request)
                or attempt.source_id != _source_id(provider_policy)
                or attempt.policy_generation != current_policy_generation()
                or attempt.source_generation
                != source_binding_generation(provider_id, attempt.source_id)
            )
            if invalid:
                raise AuthenticationAttempt.DoesNotExist
            attempt.consumed_at = now
            attempt.save(update_fields=("consumed_at",))
    except AuthenticationAttempt.DoesNotExist:
        return _callback_error(request, "invalid_state", status=400)

    runtime = get_authentication_provider_lookup().get(provider_id)
    if runtime is None:
        return _callback_error(
            request,
            "provider_unavailable",
            status=503,
            correlation_id=attempt.correlation_id,
            retryable=True,
            return_url=attempt.return_url,
        )
    try:
        result = cast(RedirectAuthenticationProvider, runtime).complete(
            RedirectCallbackContext(
                provider_id=provider_id,
                source_id=attempt.source_id,
                attempt_id=str(attempt.pk),
                correlation_id=str(attempt.correlation_id),
                deadline=attempt.expires_at,
                callback_parameters={
                    key: request.GET.get(key, "") for key in request.GET
                },
                callback_url=_callback_url(provider_id),
            )
        )
    except Exception:
        log.warning(
            "authentication_provider_failed",
            extra={
                "provider_id": provider_id,
                "stage": "redirect_callback",
                "correlation_id": str(attempt.correlation_id),
            },
        )
        return _callback_error(
            request,
            "provider_unavailable",
            status=503,
            correlation_id=attempt.correlation_id,
            retryable=True,
            return_url=attempt.return_url,
        )
    if isinstance(result, AuthenticationFailure):
        return _callback_provider_failure(
            request,
            result,
            correlation_id=attempt.correlation_id,
            return_url=attempt.return_url,
        )
    if not isinstance(result, VerifiedIdentity):
        return _callback_error(
            request,
            "invalid_result",
            status=502,
            correlation_id=attempt.correlation_id,
            return_url=attempt.return_url,
        )
    try:
        result.validate_for(
            provider_id=provider_id, source_id=attempt.source_id
        )
    except InvalidAuthenticationResultError:
        return _callback_error(
            request,
            "invalid_result",
            status=502,
            correlation_id=attempt.correlation_id,
            return_url=attempt.return_url,
        )
    try:
        provisioned = provision_verified_identity(
            result,
            provider_policy,
            correlation_id=str(attempt.correlation_id),
            attempt_generation=attempt.pk,
        )
    except Exception:
        log.warning(
            "authentication_provisioning_failed",
            extra={
                "provider_id": provider_id,
                "stage": "provisioning",
                "correlation_id": str(attempt.correlation_id),
            },
        )
        return _callback_error(
            request,
            "provisioning_failed",
            status=403,
            correlation_id=attempt.correlation_id,
            return_url=attempt.return_url,
        )
    if (
        attempt.policy_generation != current_policy_generation()
        or attempt.source_generation
        != source_binding_generation(provider_id, attempt.source_id)
    ):
        return _callback_error(
            request,
            "authentication_state_changed",
            status=409,
            correlation_id=attempt.correlation_id,
            retryable=True,
            return_url=attempt.return_url,
        )
    _establish_session(
        request,
        user=provisioned.user,
        provider_id=provider_id,
        source_id=attempt.source_id,
        identity_link=provisioned.identity_link,
    )
    return HttpResponse(
        status=302,
        headers={"Location": attempt.return_url, "Cache-Control": "no-store"},
    )


signup = SignupView.as_api_view(client=Client.BROWSER)
