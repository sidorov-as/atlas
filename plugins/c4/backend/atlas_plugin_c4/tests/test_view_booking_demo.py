"""A saved view over the booking demo catalog (tasks 9.3 of the view builder change)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from server.apps.catalog.models import CatalogEntity

pytestmark = pytest.mark.django_db

VIEWS_URL = "/api/plugins/atlas.c4/views/"
SELECTION = [
    ("component", "booking-service"),
    ("component", "payment-service"),
    ("resource", "booking-events-queue"),
    ("resource", "payments-db"),
    ("api", "stripe-api"),
]


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def render(payload, *, format):
        calls.append(payload)
        return b"<svg />"

    monkeypatch.setattr("atlas_plugin_c4.c4.render", render)
    return calls


@pytest.fixture
def client(dmr_client):
    """Seeds the demo first: the seed flushes the database, so nothing may be created before it."""
    call_command("seed_booking_demo", "--yes")
    user = get_user_model().objects.create_user(username="viewer", password="pw12345!")
    dmr_client.force_login(user)
    return dmr_client


def _ids(selection):
    return [
        str(CatalogEntity.objects.get(kind=kind, name=name).id)
        for kind, name in selection
    ]


def _view(entities):
    return {
        "name": "Booking payments",
        "description": "",
        "settings": {
            "level": "components",
            "selection": "selected",
            "entities": entities,
            "relationships": "declared",
        },
    }


def test_five_selected_entities_give_the_four_declared_relationships(client, captured):
    response = client.post(VIEWS_URL, data=_view(_ids(SELECTION)), format="json")
    assert response.status_code == 201, response.content
    view_id = response.json()["id"]

    assert client.get(f"{VIEWS_URL}{view_id}/diagram/").status_code == 200
    payload = captured[-1]
    assert len(payload["relationships"]) == 4


def test_removing_an_entity_leaves_its_neighbour_isolated(client, captured):
    remaining = [pair for pair in SELECTION if pair[1] != "booking-service"]
    view_id = client.post(VIEWS_URL, data=_view(_ids(SELECTION)), format="json").json()[
        "id"
    ]
    response = client.put(
        f"{VIEWS_URL}{view_id}/", data=_view(_ids(remaining)), format="json"
    )
    assert response.status_code == 200, response.content

    assert client.get(f"{VIEWS_URL}{view_id}/diagram/").status_code == 200
    payload = captured[-1]
    # payment-service keeps its two relationships; booking-events-queue lost its
    # only declared one but stays on the diagram as an unconnected node.
    assert len(payload["relationships"]) == 2
    elements = payload["elements"] + [
        element
        for boundary in payload["boundaries"]
        for element in boundary["elements"]
    ]
    assert len(elements) == 4
    connected = {
        endpoint
        for relationship in payload["relationships"]
        for endpoint in (relationship["from"], relationship["to"])
    }
    isolated = [e["label"] for e in elements if e["alias"] not in connected]
    assert len(isolated) == 1 and "booking-events-queue" in isolated[0].lower().replace(
        " ", "-"
    )
