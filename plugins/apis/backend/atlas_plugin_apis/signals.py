"""Wires `ApiDetails` writes to `recompute_relations` and to the OpenAPI
endpoint importer and the AsyncAPI
operation importer — split
out of `server.apps.catalog.signals`.

Connected via `post_save` on `ApiDetails` rather than called explicitly from
each write path, so every way an entity's kind-specific data can be
written — the CRUD API now, ingestion later — recomputes relations (and
syncs endpoints) the same way without every call site needing to remember to
do it.

`Relation` has a real `on_delete=CASCADE` FK to `CatalogEntity` on both sides
so a deleted entity's relation rows are
removed by the database — no `post_delete` cleanup needed here anymore.
"""

from atlas_plugin_api import recompute_relations
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import asyncapi_import, openapi_import
from .models import ApiDetails

# `sync_endpoints_from_spec`/`sync_operations_from_spec` each persist their own
# outcome via `details.save(update_fields=[...])` limited to exactly their own
# two status fields. That save re-fires this same `post_save`
# signal for *both* receivers; without this guard either receiver would re-run
# its sync off the other's status self-save, which would call
# `details.save(update_fields=[...])` again, forever. One shared set covers
# both self-writes so either receiver recognizes "a known sync-status
# self-write", not just its own.
_SYNC_STATUS_FIELDS = frozenset(
    {
        "endpoints_synced_at",
        "endpoints_sync_failed",
        "operations_synced_at",
        "operations_sync_failed",
        "resolved_base_url",
        "resolved_protocol",
    }
)


@receiver(post_save, sender=ApiDetails)
def _recompute_on_save(sender, instance, **kwargs):
    recompute_relations(instance.entity)


@receiver(post_save, sender=ApiDetails)
def _sync_endpoints_on_save(sender, instance, update_fields, **kwargs):
    if update_fields is not None and set(update_fields) <= _SYNC_STATUS_FIELDS:
        return
    openapi_import.sync_endpoints_from_spec(instance)


@receiver(post_save, sender=ApiDetails)
def _sync_operations_on_save(sender, instance, update_fields, **kwargs):
    if update_fields is not None and set(update_fields) <= _SYNC_STATUS_FIELDS:
        return
    asyncapi_import.sync_operations_from_spec(instance)
