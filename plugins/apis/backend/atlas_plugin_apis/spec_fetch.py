"""Fetching URL-sourced API spec content —
split out of `server.apps.catalog.spec_fetch`.

Shared by the CRUD API's synchronous first-fetch on save (`atlas_plugin_apis.api.views`)
and the ingestor's periodic refresh (`atlas_plugin_ingestion.pipeline`) — the same
fetch-and-validate rule applies whether `spec_url` is resolved on save or
re-checked in the poll loop: a non-empty response that parses as YAML-or-JSON,
within size/nesting limits, is accepted verbatim, anything else is treated as
a failed resolution. This is a deliberately cheap gate, not spec validation
it only exists to stop an error page, an empty body,
or a YAML-bomb-style document from clobbering a good snapshot.

`fetch_spec_content` fetches through `atlas_plugin_api.safe_http.safe_request`
rather than a bare `requests.get`: HTTPS-only and
non-reserved-address by default, with `ATLAS_APIS_SPEC_URL_ALLOWLIST`
exempting specific operator-configured hosts from both restrictions (e.g. an
internal Git or artifact server intentionally reachable only over HTTP or a
private address). A fetch rejected for any of these reasons is treated
exactly like any other failed resolution — see the module-level exception
handling below.
"""

import logging
from urllib.parse import urlsplit

import yaml
from atlas_plugin_api import (
    SafeHttpError,
    add_dry_run_warning,
    is_dry_run,
    safe_request,
)
from django.conf import settings
from django.utils import timezone

from atlas_plugin_apis.models import ApiDetails

logger = logging.getLogger("atlas_plugin_apis")

REQUEST_TIMEOUT_SECONDS = 10

# Generous on purpose (some real-world specs are
# multi-MB) — a named constant so it's easy to reconsider, not a number
# buried in the fetch call.
MAX_SPEC_RESPONSE_BYTES = 20 * 1024 * 1024

# Bounds on the *parsed* structure, not just the raw byte count —
# a small YAML document could still stay under MAX_SPEC_RESPONSE_BYTES while
# exploding into an implausibly deep or large structure once loaded (a
# YAML-bomb-style document).
MAX_SPEC_PARSE_DEPTH = 100
MAX_SPEC_PARSE_NODES = 200_000


def _allowlisted_spec_hosts() -> frozenset[str]:
    """Operator-configured hosts exempted from the HTTPS-only and
    non-reserved-address requirements when fetching `spec_url`
    (`ATLAS_APIS_SPEC_URL_ALLOWLIST`). HTTPS-only by default, operator allowlist
    for exceptions. Empty (deny) by default."""
    return frozenset(getattr(settings, "ATLAS_APIS_SPEC_URL_ALLOWLIST", ()))


def _within_parse_limits(value: object) -> bool:
    """Reject a parsed YAML/JSON document that's implausibly deep or large
    (not just success/failure of yaml.safe_load). Iterative, not
    recursive, so this check itself can't be defeated by a deeply nested
    document triggering a `RecursionError` before the depth limit is even
    reached."""
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if depth > MAX_SPEC_PARSE_DEPTH or nodes > MAX_SPEC_PARSE_NODES:
            return False
        if isinstance(node, dict):
            stack.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            stack.extend((child, depth + 1) for child in node)
    return True


def fetch_spec_content(url: str) -> str | None:
    """Fetch `url` and return its text, or `None` if the fetch failed, was
    rejected as unsafe, or the body is unusable."""
    hostname = urlsplit(url).hostname
    allowlisted = hostname is not None and hostname in _allowlisted_spec_hosts()

    try:
        response = safe_request(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_response_bytes=MAX_SPEC_RESPONSE_BYTES,
            allow_http=allowlisted,
            exempt_hosts=[hostname] if allowlisted else (),
        )
    except SafeHttpError:
        logger.warning("Rejected or failed to fetch spec_url %s", url, exc_info=True)
        return None

    if not (200 <= response.status_code < 300):
        logger.warning(
            "Failed to fetch spec_url %s: HTTP %s", url, response.status_code
        )
        return None

    text = response.content.decode("utf-8", errors="replace")
    if not text.strip():
        return None

    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError:
        return None

    if not _within_parse_limits(parsed):
        logger.warning(
            "Rejected spec_url %s: parsed content exceeds size/nesting limits", url
        )
        return None

    return text


def resolve_api_spec_url(instance: ApiDetails) -> None:
    """Synchronously fetch `instance.spec_url`, updating the resolved snapshot in place."""
    content = fetch_spec_content(instance.spec_url)
    if content is None:
        instance.spec_resolve_failed = True
    else:
        instance.spec_content = content
        instance.spec_resolved_at = timezone.now()
        instance.spec_resolve_failed = False


def apply_api_spec_source(
    instance: ApiDetails, spec_source: str, spec_url: str, spec_content: str
) -> None:
    """Set `instance`'s spec-source fields, resolving `spec_url` synchronously when source is `url`.

    Shared by the CRUD API's create/patch handlers and the ingestor's manifest
    upsert — both apply a spec-source change the same way.
    """
    instance.spec_source = spec_source
    if spec_source == ApiDetails.SPEC_SOURCE_URL:
        instance.spec_url = spec_url
        if is_dry_run():
            add_dry_run_warning(
                f"The spec at {spec_url} would be fetched on a real write; "
                "a dry-run does not make that request"
            )
        else:
            resolve_api_spec_url(instance)
    elif spec_source == ApiDetails.SPEC_SOURCE_INLINE:
        instance.spec_url = ""
        instance.spec_content = spec_content
        instance.spec_resolved_at = None
        instance.spec_resolve_failed = False
    else:
        instance.spec_url = ""
        instance.spec_content = ""
        instance.spec_resolved_at = None
        instance.spec_resolve_failed = False
