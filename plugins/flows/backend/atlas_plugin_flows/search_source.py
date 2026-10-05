"""Flows as searchable documents (`add-search-sources`).

One document per flow, id `flow:<flow pk>`: the flow's name is the title, and
its description, documentation and the visible text of its steps are the body.
A hit opens the whole flow, never a specific step.

Visibility follows the flows plugin's existing read rule: any authenticated
user may read any flow (`SessionAuth` on the read routes). A flow also needs an
active owning system, so removing the system drops its flows from search.
`resolve` re-loads live rows, so flows deleted since indexing are dropped even
if the index is stale.
"""

from collections.abc import Iterable, Iterator, Sequence
from typing import Any, ClassVar

from atlas_plugin_api import (
    KIND_SYSTEM,
    STATUS_ACTIVE,
    SearchDocument,
    SearchHit,
    get_catalog_entity_model,
    split_document_id,
)

from .models import Flow

KIND_FLOW = "flow"

_STEP_TEXT_KEYS = ("title", "summary", "external_label")


def flatten_step_text(steps: object) -> str:
    """Visible text of a flow's steps: each step's title, summary and external label.

    Isolated here so a change of the steps' JSON shape breaks one function and
    its tests, not search. Anything unexpected (non-list steps, non-object
    steps, non-string or blank values) is skipped rather than raised.
    """
    if not isinstance(steps, list):
        return ""
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        for key in _STEP_TEXT_KEYS:
            value = step.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
    return "\n".join(lines)


def _text(flow: Flow) -> str:
    return "\n\n".join(
        part
        for part in (
            flow.description,
            flow.documentation,
            flatten_step_text(flow.steps),
        )
        if part
    )


def _document(flow: Flow) -> SearchDocument:
    return SearchDocument(
        id=f"{KIND_FLOW}:{flow.pk}",
        kind=KIND_FLOW,
        title=flow.name,
        body=_text(flow),
        summary=flow.description or None,
    )


def _pks(ids: Sequence[str]) -> list[int]:
    pks: list[int] = []
    for document_id in ids:
        try:
            kind, key = split_document_id(document_id)
            if kind == KIND_FLOW:
                pks.append(int(key))
        except ValueError:
            continue
    return pks


def _searchable():
    return Flow.objects.filter(system__status=STATUS_ACTIVE).select_related("system")


class FlowSearchSource:
    id = "atlas.flows"
    kinds = (KIND_FLOW,)
    kind_labels: ClassVar[dict[str, str]] = {KIND_FLOW: "Flow"}

    @property
    def watched_models(self) -> tuple[str, ...]:
        # The owning system is watched because its removal or revival changes
        # whether its flows are searchable.
        return (Flow._meta.label, get_catalog_entity_model()._meta.label)

    def document_ids_for_instance(self, instance: Any) -> Iterable[str]:
        # Also for deleted rows: `documents` then omits the id and the indexer
        # deletes it.
        if isinstance(instance, Flow):
            return [f"{KIND_FLOW}:{instance.pk}"]
        if getattr(instance, "kind", None) != KIND_SYSTEM:
            return []
        return [
            f"{KIND_FLOW}:{pk}"
            for pk in Flow.objects.filter(system_id=instance.pk).values_list(
                "pk", flat=True
            )
        ]

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        return [_document(flow) for flow in _searchable().filter(pk__in=_pks(ids))]

    def all_documents(self) -> Iterator[SearchDocument]:
        for flow in _searchable().iterator():
            yield _document(flow)

    def resolve(self, ids: Sequence[str], actor: Any) -> Sequence[SearchHit]:
        if not getattr(actor, "is_authenticated", False):
            return []
        return [
            SearchHit(
                id=f"{KIND_FLOW}:{flow.pk}",
                kind=KIND_FLOW,
                # The dialog shows only the title, so the live system name goes there.
                title=f"{flow.name} — {flow.system.name}",
                link=f"/flows/{flow.pk}",
                text=_text(flow),
                summary=flow.description or None,
            )
            for flow in _searchable().filter(pk__in=_pks(ids))
        ]


flow_search_source = FlowSearchSource()
