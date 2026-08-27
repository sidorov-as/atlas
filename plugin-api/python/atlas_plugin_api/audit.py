"""Entity lifecycle audit-record read access (`entity-removal-lifecycle` spec:
"Remove/Revive/Purge are audited and visible on a History tab").

Stands in for `server.apps.catalog.models.audit.EntityAuditRecord` — every
Create/Update/Delete/Remove/Revive/Purge the Entity Service performs already
writes one of these rows (`entity_service.py`'s `_audit_actor`-tagged
`EntityAuditRecord.objects.create(...)` calls), but nothing reads them back
out until now. Like `relations.py`'s `get_relation_model()`, this publishes a
lazy Django-app-registry accessor rather than importing the concrete model,
so `atlas_plugin_api` never depends on `server`.
"""

from typing import Any

from django.apps import apps as _django_apps

AUDIT_RECORD_LABEL = "catalog.EntityAuditRecord"


def get_audit_record_model() -> type:
    """Resolve Core's concrete `EntityAuditRecord` model via Django's app registry,
    the same lazy-resolution mechanism `get_relation_model()` uses. Only callable
    after `django.setup()` — from inside a function body, never cached at plugin
    module import time.
    """
    return _django_apps.get_model(AUDIT_RECORD_LABEL)


def _actor_label(actor: Any) -> str | None:
    """A human-readable label for an audit record's `actor` — the linked Actor
    entity's display name/ref if the account is linked to one (`ActorDetails.
    account`), falling back to the login username, or `None` when `actor` is
    unset (an ingestion-triggered action, `EntityService`'s `_audit_actor`
    returns `None` for any unauthenticated/absent actor — auto-remove/-revive
    during ingestion reconciliation is the only such path once write
    permission is enforced)."""
    if actor is None:
        return None
    catalog_actor = getattr(actor, "catalog_actor", None)
    if catalog_actor is not None:
        entity = catalog_actor.entity
        return entity.title or entity.name
    return actor.get_username()


def entity_history(entity: Any) -> list[tuple[str, str | None, Any]]:
    """Every `EntityAuditRecord` for `entity`, newest first, as `(action, actor_label,
    timestamp)` tuples — `entity_id` is a plain UUID column (not a FK), matching
    `EntityAuditRecord`'s own append-only, survives-the-entity design.
    """
    records = (
        get_audit_record_model()
        .objects.filter(entity_id=entity.id)
        .select_related("actor__catalog_actor__entity")
    )
    return [
        (record.action, _actor_label(record.actor), record.timestamp)
        for record in records
    ]
