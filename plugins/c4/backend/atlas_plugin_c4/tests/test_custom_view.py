"""Custom view builder (`c4-custom-view-diagram` spec)."""

from uuid import uuid4

import pytest
from atlas_plugin_api import STATUS_REMOVED, get_architecture_relationship_model
from c4.converters.json.converter import diagram_from_dict
from server.apps.catalog.tests.factories import (
    create_actor,
    create_api,
    create_component,
    create_group,
    create_resource,
    create_system,
)

from atlas_plugin_c4 import c4
from atlas_plugin_c4.custom_view import CustomViewRequest, build_custom_view
from atlas_plugin_c4.errors import CustomViewError

pytestmark = pytest.mark.django_db

ArchitectureRelationship = get_architecture_relationship_model()


def declare(source, target, label="Calls"):
    return ArchitectureRelationship.objects.create(
        source=source, target=target, label=label
    )


def view(*entities, **overrides):
    values = {
        "level": "components",
        "selection": "selected",
        "entities": tuple(e.id for e in entities),
    } | overrides
    return CustomViewRequest(**values)


def aliases(payload):
    found = [item["alias"] for item in payload["elements"]]
    for boundary in payload.get("boundaries", []):
        found += [item["alias"] for item in boundary["elements"]]
    return set(found)


def edges(payload):
    return {(r["from"], r["to"]) for r in payload["relationships"]}


def a(entity):
    return c4.alias(entity.kind, entity.id)


@pytest.fixture
def booking(db):
    team = create_group(name="team")
    system = create_system(name="booking", owner=team)
    other = create_system(name="payments", owner=team)
    api = create_api(name="booking-api", owner=team, system=system)
    db_ = create_resource(name="booking-db", owner=team, system=system)
    payment = create_component(name="payment", owner=team, system=other)
    worker = create_component(name="worker", owner=team, system=system)
    declare(api, db_)
    declare(api, payment)
    declare(api, worker)
    declare(payment, db_)
    return {
        "team": team,
        "system": system,
        "other": other,
        "api": api,
        "db": db_,
        "payment": payment,
        "worker": worker,
    }


def test_selected_only_draws_edges_between_selected_nodes(booking):
    b = booking
    payload = build_custom_view(view(b["api"], b["db"], b["payment"]))
    assert aliases(payload) == {a(b["api"]), a(b["db"]), a(b["payment"])}
    assert edges(payload) == {
        (a(b["api"]), a(b["db"])),
        (a(b["api"]), a(b["payment"])),
        (a(b["payment"]), a(b["db"])),
    }
    diagram_from_dict(payload)


def test_selected_only_keeps_isolated_node(booking):
    b = booking
    payload = build_custom_view(view(b["db"], b["worker"]))
    assert aliases(payload) == {a(b["db"]), a(b["worker"])}
    assert edges(payload) == set()


def test_neighborhood_depth_and_direction(booking):
    b = booking
    one = build_custom_view(view(b["api"], selection="neighborhood"))
    assert aliases(one) == {a(b[k]) for k in ("api", "db", "payment", "worker")}
    out = build_custom_view(
        view(b["db"], selection="neighborhood", direction="outgoing")
    )
    assert aliases(out) == {a(b["db"])}
    incoming = build_custom_view(
        view(b["db"], selection="neighborhood", direction="incoming")
    )
    assert aliases(incoming) == {a(b[k]) for k in ("db", "api", "payment")}
    two = build_custom_view(
        view(b["worker"], selection="neighborhood", direction="both", depth=2)
    )
    assert a(b["db"]) in aliases(two)
    unlimited = build_custom_view(
        view(b["worker"], selection="neighborhood", depth=None)
    )
    assert len(aliases(unlimited)) == 4


def test_excluded_types_are_not_bridges_and_roots_survive(booking):
    b = booking
    request = view(
        b["worker"],
        selection="neighborhood",
        depth=3,
        entity_types=frozenset({"component"}),
    )
    # worker - api - (db, payment): the api is excluded so nothing is reached.
    assert aliases(build_custom_view(request)) == {a(b["worker"])}
    root_resource = view(
        b["db"],
        selection="neighborhood",
        entity_types=frozenset({"component"}),
    )
    assert a(b["db"]) in aliases(build_custom_view(root_resource))


def test_derived_relationships_and_declared_precedence(booking):
    b = booking
    b["worker"].component_details.depends_on.add(b["db"])
    declared_only = build_custom_view(view(b["worker"], b["db"]))
    assert edges(declared_only) == set()
    both = build_custom_view(
        view(b["worker"], b["db"], relationships="declared_and_derived")
    )
    assert edges(both) == {(a(b["worker"]), a(b["db"]))}
    declare(b["worker"], b["db"], label="Writes")
    payload = build_custom_view(
        view(b["worker"], b["db"], relationships="declared_and_derived")
    )
    assert [r["label"] for r in payload["relationships"]] == ["Writes"]


def test_actors_are_leaves_and_never_inferred(booking):
    b = booking
    guest = create_actor(name="guest", display_name="Guest")
    declare(guest, b["api"])
    declare(guest, b["payment"])
    start = view(b["worker"], selection="neighborhood", depth=3)
    reached = aliases(build_custom_view(start))
    assert a(guest) in reached
    only_api = build_custom_view(view(b["api"], selection="neighborhood"))
    assert a(guest) in aliases(only_api)
    disabled = build_custom_view(
        view(
            b["api"],
            selection="neighborhood",
            entity_types=frozenset({"component", "resource", "api"}),
        )
    )
    assert a(guest) not in aliases(disabled)
    as_root = build_custom_view(view(guest, selection="neighborhood"))
    assert {a(guest), a(b["api"]), a(b["payment"])} <= aliases(as_root)
    # The owning group never shows up.
    assert a(b["team"]) not in aliases(only_api)


def test_actor_is_not_a_bridge(booking):
    b = booking
    guest = create_actor(name="guest", display_name="Guest")
    declare(guest, b["api"])
    declare(guest, b["payment"])
    lone = create_component(name="lone", owner=b["team"], system=b["other"])
    declare(guest, lone)
    reached = aliases(
        build_custom_view(view(b["worker"], selection="neighborhood", depth=2))
    )
    assert a(guest) in reached
    assert a(lone) not in reached


def test_systems_level_aggregates_and_collapses_actor_edges(booking):
    b = booking
    guest = create_actor(name="guest", display_name="Guest")
    declare(guest, b["payment"])
    payload = build_custom_view(
        view(b["system"], level="systems", selection="neighborhood")
    )
    assert aliases(payload) == {a(b["system"]), a(b["other"])}
    assert edges(payload) == {
        (a(b["system"]), a(b["other"])),
        (a(b["other"]), a(b["system"])),
    }
    other = build_custom_view(
        view(b["other"], level="systems", selection="neighborhood")
    )
    assert a(guest) in aliases(other)
    assert (a(guest), a(b["other"])) in edges(other)
    diagram_from_dict(payload)


def test_boundaries_hold_only_visible_elements(booking):
    b = booking
    loose = create_resource(name="loose", owner=b["team"])
    payload = build_custom_view(view(b["api"], b["payment"], loose))
    by_label = {
        boundary["label"]: {e["alias"] for e in boundary["elements"]}
        for boundary in payload["boundaries"]
    }
    assert by_label == {
        "booking": {a(b["api"])},
        "payments": {a(b["payment"])},
    }
    assert a(loose) in {e["alias"] for e in payload["elements"]}
    diagram_from_dict(payload)


def test_resource_rendering_follows_type(booking):
    b = booking
    queue = create_resource(name="q", owner=b["team"], type="queue", system=b["system"])
    payload = build_custom_view(view(b["db"], queue))
    types = {
        e["alias"]: e["type"]
        for boundary in payload["boundaries"]
        for e in boundary["elements"]
    }
    assert types[a(b["db"])] == "ComponentDb"
    assert types[a(queue)] == "ComponentQueue"


def test_output_is_deterministic(booking):
    b = booking
    request = view(
        b["api"], selection="neighborhood", relationships="declared_and_derived"
    )
    assert build_custom_view(request) == build_custom_view(request)


def test_node_limit(booking, settings, monkeypatch):
    b = booking
    request = view(b["api"], selection="neighborhood")
    monkeypatch.setattr(
        c4, "plugin_config", lambda: c4.C4PluginConfig.model_validate({"maxNodes": 3})
    )
    with pytest.raises(CustomViewError) as raised:
        build_custom_view(request)
    assert raised.value.extra == {"limit": 3, "count": 4}
    monkeypatch.setattr(
        c4, "plugin_config", lambda: c4.C4PluginConfig.model_validate({"maxNodes": 4})
    )
    build_custom_view(request)


def test_selection_errors_name_the_entity(booking):
    b = booking
    missing = uuid4()
    with pytest.raises(CustomViewError) as raised:
        build_custom_view(
            CustomViewRequest("components", "selected", (b["api"].id, missing))
        )
    assert raised.value.extra["entity"] == str(missing)
    b["worker"].status = STATUS_REMOVED
    b["worker"].save()
    with pytest.raises(CustomViewError) as raised:
        build_custom_view(view(b["worker"]))
    assert raised.value.code == "unknown_entity"
    with pytest.raises(CustomViewError) as raised:
        build_custom_view(view(b["system"], b["api"]))
    assert raised.value.code == "mixed_level_selection"
    with pytest.raises(CustomViewError) as raised:
        build_custom_view(view(b["api"], level="systems"))
    assert raised.value.extra["entity"] == str(b["api"].id)


def test_removed_entities_never_appear(booking):
    b = booking
    b["db"].status = STATUS_REMOVED
    b["db"].save()
    payload = build_custom_view(view(b["api"], selection="neighborhood"))
    assert a(b["db"]) not in aliases(payload)


def test_system_depth_counts_aggregated_hops(booking):
    b = booking
    third = create_system(name="shipping", owner=b["team"])
    shipper = create_component(name="shipper", owner=b["team"], system=third)
    declare(b["payment"], shipper)
    one = build_custom_view(
        view(
            b["system"], level="systems", selection="neighborhood", direction="outgoing"
        )
    )
    assert aliases(one) == {a(b["system"]), a(b["other"])}
    two = build_custom_view(
        view(
            b["system"],
            level="systems",
            selection="neighborhood",
            direction="outgoing",
            depth=2,
        )
    )
    assert aliases(two) == {a(b["system"]), a(b["other"]), a(third)}


def test_unlimited_depth_is_rejected_above_the_limit(booking, monkeypatch):
    b = booking
    monkeypatch.setattr(
        c4, "plugin_config", lambda: c4.C4PluginConfig.model_validate({"maxNodes": 3})
    )
    with pytest.raises(CustomViewError) as raised:
        build_custom_view(view(b["worker"], selection="neighborhood", depth=None))
    assert raised.value.code == "node_limit_exceeded"


def test_empty_entity_types_disable_actors_but_keep_systems(booking):
    b = booking
    guest = create_actor(name="guest", display_name="Guest")
    declare(guest, b["payment"])
    payload = build_custom_view(
        view(
            b["system"],
            level="systems",
            selection="neighborhood",
            entity_types=frozenset(),
        )
    )
    assert aliases(payload) == {a(b["system"]), a(b["other"])}
    assert a(guest) not in aliases(
        build_custom_view(
            view(
                b["other"],
                level="systems",
                selection="neighborhood",
                entity_types=frozenset(),
            )
        )
    )


def test_booking_example_from_the_design_brief(db):
    team = create_group(name="booking-team")
    booking = create_system(name="booking", owner=team)
    payments = create_system(name="payments", owner=team)
    notifications = create_system(name="notifications", owner=team)
    api = create_component(name="Booking API", owner=team, system=booking)
    database = create_resource(name="Booking DB", owner=team, system=booking)
    events = create_resource(
        name="Booking Events", owner=team, system=booking, type="queue"
    )
    payment = create_component(name="Payment Service", owner=team, system=payments)
    worker = create_component(
        name="Notification Worker", owner=team, system=notifications
    )
    declare(api, payment, "Charges payment")
    declare(api, database, "Stores reservations")
    declare(api, events, "Publishes booking events")
    declare(events, worker, "Delivers events")

    full = build_custom_view(view(api, database, events, payment, worker))
    assert len(aliases(full)) == 5
    assert len(full["relationships"]) == 4

    without_events = build_custom_view(view(api, database, payment, worker))
    assert aliases(without_events) == {a(api), a(database), a(payment), a(worker)}
    assert edges(without_events) == {(a(api), a(payment)), (a(api), a(database))}
    assert not any(
        a(worker) in pair for pair in edges(without_events)
    )  # still visible, but isolated
