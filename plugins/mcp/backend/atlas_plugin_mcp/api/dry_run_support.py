"""Shared pieces of the `dryRun` flag on the authoring writes
(`mcp-write-preview` spec): the field-level diff and the response envelope.

The rollback itself is `atlas_plugin_api.dry_run()`; this only shapes what a
controller reports from inside it.
"""

from typing import Any

from atlas_plugin_api import DryRunContext
from pydantic import BaseModel

from .schemas import DryRunOut, FieldChangeOut


def dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(by_alias=True, mode="json")


def _flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}{key}"
        if isinstance(item, dict) and item:
            flat.update(_flatten(item, f"{path}."))
        else:
            flat[path] = item
    return flat


def field_changes(
    before: dict[str, Any] | None, after: dict[str, Any] | None
) -> list[FieldChangeOut]:
    """Leaf-level differences; a create has no `before`, a delete no
    `after`."""
    old = _flatten(before or {})
    new = _flatten(after or {})
    return [
        FieldChangeOut(field=path, before=old.get(path), after=new.get(path))
        for path in [*old, *(path for path in new if path not in old)]
        if old.get(path) != new.get(path)
    ]


def dry_run_out(
    *,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    context: DryRunContext,
) -> DryRunOut:
    """`after` of a create carries a throwaway id from the rolled-back row;
    it is reported as null."""
    if after is not None and before is None:
        after = {**after, "id": None}
    return DryRunOut(
        result=after,
        changes=field_changes(before, after),
        warnings=list(context.warnings),
    )
