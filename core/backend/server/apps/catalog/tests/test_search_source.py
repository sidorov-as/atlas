"""Catalog search source (`search-catalog-source` spec)."""

import pytest
from atlas_plugin_api import get_search_source_lookup

from server.apps.catalog.models import KIND_ACTOR, CatalogEntity
from server.apps.catalog.search_source import catalog_search_source as source
from server.apps.catalog.services.entity_service import EntityService
from server.apps.catalog.tests.factories import create_component, create_system

pytestmark = pytest.mark.django_db


def _doc_id(entity):
    return f"{entity.kind}:{entity.pk}"


def test_source_is_registered_by_the_catalog_runtime_hook():
    from server.apps.catalog.plugin import register_runtime

    lookup = get_search_source_lookup()
    if lookup.get(source.id) is None:
        register_runtime()
    assert lookup.get(source.id) is source
    assert lookup.for_kind("component") is source


def test_document_has_name_as_title_and_description_plus_documentation_as_body(
    group,
):
    entity = create_system(
        name="billing",
        owner=group,
        description="Handles invoices",
        documentation="Retries use exponential backoff",
    )

    (doc,) = source.documents([_doc_id(entity)])

    assert doc.id == f"system:{entity.pk}"
    assert doc.kind == "system"
    assert doc.title == "billing"
    assert "Handles invoices" in doc.body
    assert "exponential backoff" in doc.body


def test_all_documents_skip_removed_and_user_entities(group, system):
    removed = create_system(name="gone", owner=group)
    removed.status = CatalogEntity.STATUS_REMOVED
    removed.save()
    CatalogEntity.objects.create(kind=KIND_ACTOR, name="someone")

    ids = {d.id for d in source.all_documents()}

    assert _doc_id(system) in ids
    assert _doc_id(group) in ids
    assert _doc_id(removed) not in ids
    assert not any(i.startswith("user:") for i in ids)


def test_instance_maps_to_its_document_id_but_users_do_not(group):
    assert list(source.document_ids_for_instance(group)) == [_doc_id(group)]
    actor = CatalogEntity(kind=KIND_ACTOR, name="someone")
    assert list(source.document_ids_for_instance(actor)) == []
    assert source.watched_models == ("catalog.CatalogEntity",)


def test_removal_and_revival_change_the_documents(system, superuser_account):
    service = EntityService()
    doc_id = _doc_id(system)
    assert [d.id for d in source.documents([doc_id])] == [doc_id]

    service.remove(entity_id=system.id, actor=superuser_account)
    # The removed entity still maps to its id, so the indexer deletes it.
    assert list(source.document_ids_for_instance(system)) == [doc_id]
    assert list(source.documents([doc_id])) == []

    service.revive(entity_id=system.id, actor=superuser_account)
    assert [d.id for d in source.documents([doc_id])] == [doc_id]


def test_resolve_builds_hit_with_link_and_drops_removed_entities(
    group, system, superuser_account
):
    live = create_component(
        name="checkout", owner=group, system=system, description="Cart flow"
    )
    gone = create_component(name="legacy", owner=group, system=system)
    gone.status = CatalogEntity.STATUS_REMOVED
    gone.save()

    hits = source.resolve(
        [_doc_id(live), _doc_id(gone), "component:not-a-uuid", "flow:1"],
        superuser_account,
    )

    assert [h.id for h in hits] == [_doc_id(live)]
    assert hits[0].link == f"/components/{live.pk}"
    assert hits[0].title == "checkout"
    assert hits[0].summary == "Cart flow"


def test_any_authenticated_actor_reads_but_anonymous_does_not(
    system, django_user_model
):
    from django.contrib.auth.models import AnonymousUser

    plain = django_user_model.objects.create_user(
        username="plain", password="x"
    )
    assert [h.id for h in source.resolve([_doc_id(system)], plain)] == [
        _doc_id(system)
    ]
    assert source.resolve([_doc_id(system)], AnonymousUser()) == []
