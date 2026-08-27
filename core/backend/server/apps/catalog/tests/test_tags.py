from server.apps.catalog.models import DEFAULT_TAG_COLOR, Tag, ensure_tags_exist


def test_new_tag_defaults_to_the_palette_default(db):
    ensure_tags_exist(["backend"])
    tag = Tag.objects.get(name="backend")
    assert tag.color == DEFAULT_TAG_COLOR


def test_color_update_accepted_for_a_palette_value(superuser_client, db):
    tag = Tag.objects.create(name="infra")
    response = superuser_client.patch(f"/api/tags/{tag.id}/", {"color": "blue"})
    assert response.status_code == 200
    tag.refresh_from_db()
    assert tag.color == "blue"


def test_color_update_rejected_for_a_non_palette_value(superuser_client, db):
    tag = Tag.objects.create(name="infra")
    response = superuser_client.patch(
        f"/api/tags/{tag.id}/", {"color": "#ff00ff"}
    )
    assert response.status_code == 400
    tag.refresh_from_db()
    assert tag.color == DEFAULT_TAG_COLOR


def test_color_update_requires_superuser(owner_client, db):
    tag = Tag.objects.create(name="infra")
    response = owner_client.patch(f"/api/tags/{tag.id}/", {"color": "blue"})
    assert response.status_code == 403
