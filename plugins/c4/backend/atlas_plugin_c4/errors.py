"""Structured errors for the custom view endpoint.

Bodies reuse the ``{"detail": [{"msg", "type", ...}]}`` shape of dmr's
``ErrorModel``; ``type`` carries the machine-readable code and any extra keys
(``entity``, ``limit``, ``count``) give clients what they need to act.
"""

from http import HTTPStatus
from typing import Any, Literal, NotRequired, TypedDict
from uuid import UUID

CustomViewErrorCode = Literal[
    "invalid_parameters",
    "mixed_level_selection",
    "unknown_entity",
    "node_limit_exceeded",
]


class CustomViewErrorDetail(TypedDict):
    msg: str
    type: CustomViewErrorCode
    entity: NotRequired[str]
    entities: NotRequired[list[str]]
    limit: NotRequired[int]
    count: NotRequired[int]


class CustomViewErrorBody(TypedDict):
    detail: list[CustomViewErrorDetail]


class CustomViewError(Exception):
    """A request the custom view cannot serve, with its HTTP status and body."""

    def __init__(
        self,
        code: CustomViewErrorCode,
        message: str,
        *,
        status_code: HTTPStatus,
        **extra: Any,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra

    def body(self) -> CustomViewErrorBody:
        detail: dict[str, Any] = {"msg": self.message, "type": self.code, **self.extra}
        return {"detail": [detail]}  # type: ignore[list-item]


def invalid_parameters(message: str) -> CustomViewError:
    return CustomViewError(
        "invalid_parameters", message, status_code=HTTPStatus.BAD_REQUEST
    )


def mixed_level_selection(
    message: str, entities: list[UUID] | None = None
) -> CustomViewError:
    extra = {"entities": [str(pk) for pk in entities]} if entities else {}
    return CustomViewError(
        "mixed_level_selection",
        message,
        status_code=HTTPStatus.BAD_REQUEST,
        **extra,
    )


def unknown_entity(entity: UUID) -> CustomViewError:
    return CustomViewError(
        "unknown_entity",
        f"Entity {entity} does not exist or was removed",
        status_code=HTTPStatus.NOT_FOUND,
        entity=str(entity),
    )


def node_limit_exceeded(*, limit: int, count: int) -> CustomViewError:
    return CustomViewError(
        "node_limit_exceeded",
        f"The view has {count} nodes but the limit is {limit}. "
        "Reduce the depth or the selection.",
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        limit=limit,
        count=count,
    )


def incompatible_entity(entity: UUID, level: str) -> CustomViewError:
    return CustomViewError(
        "invalid_parameters",
        f"Entity {entity} cannot be selected at the {level} level",
        status_code=HTTPStatus.BAD_REQUEST,
        entity=str(entity),
    )
