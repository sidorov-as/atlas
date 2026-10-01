"""Strict key checking for `create_entity`/`update_entity`'s `spec`.

The shared `*SpecIn`/`*SpecPatch` schemas use pydantic's default
`extra="ignore"` (ingestion and the REST API depend on that), so a
misspelled or unknown `spec` key would otherwise be dropped silently and the
write would still report success. This compares the raw keys against the
target schema's declared field names and aliases *before* model validation,
without touching those shared schemas.

`relationships` is declared on the shared schemas only because ingestion
reconciles it as YAML-origin Architecture Relationships; a manual write
through MCP can never persist it, so it is always rejected here with a
pointer at the relationship tools.
"""

import difflib
from http import HTTPStatus

from dmr.errors import ErrorType, format_error
from dmr.response import APIError
from pydantic import BaseModel

RELATIONSHIPS_KEY = "relationships"

_RELATIONSHIPS_MESSAGE = (
    "`relationships` cannot be set through `spec`: manage Architecture "
    "Relationships with the `create_relationship`, `update_relationship`, "
    "and `delete_relationship` tools"
)


def writable_spec_keys(schema: type[BaseModel]) -> set[str]:
    """Every key (alias and field name) `schema` accepts, minus
    `relationships`."""
    keys: set[str] = set()
    for name, field in schema.model_fields.items():
        keys.add(name)
        if field.alias:
            keys.add(field.alias)
    keys.discard(RELATIONSHIPS_KEY)
    return keys


def _describe(key: str, allowed: set[str]) -> str:
    close = difflib.get_close_matches(key, allowed, n=1, cutoff=0.6)
    return f"{key!r} (did you mean {close[0]!r}?)" if close else repr(key)


def check_spec_keys(schema: type[BaseModel], raw: dict) -> None:
    """Raise a 400 `APIError` naming every key of `raw` that `schema` does
    not accept through MCP."""
    if RELATIONSHIPS_KEY in raw:
        raise _bad_request(_RELATIONSHIPS_MESSAGE)
    allowed = writable_spec_keys(schema)
    unknown = sorted(key for key in raw if key not in allowed)
    if unknown:
        listed = ", ".join(_describe(key, allowed) for key in unknown)
        raise _bad_request(
            f"Unknown spec field(s): {listed}. "
            f"Valid fields: {', '.join(sorted(allowed))}"
        )


def _bad_request(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.value_error),
        status_code=HTTPStatus.BAD_REQUEST,
    )
