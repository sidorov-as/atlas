"""Tag contract (`core-plugin-contract-surface` spec: "Core publishes its
plugin-facing surface as contract types").

Stands in for `server.apps.catalog.models.tag` — Core's `Tag` model can't
move here outright (a Django model needs an installed app), but
`ensure_tags_exist` needs only a real ORM `get_or_create`, available through
`get_tag_model()` the same way `get_catalog_entity_model()` resolves
`CatalogEntity` (catalog.py's docstring), so the function moves here
outright. `TAG_PALETTE`/`DEFAULT_TAG_COLOR` are plain constants (no Django
dependency) republished here as their single source of truth;
`server.apps.catalog.models.tag` re-exports all three for Core's own
internal call sites.
"""

from django.apps import apps as _django_apps

TAG_LABEL = "catalog.Tag"

# Fixed named palette — keep in sync with
# `TAG_PALETTE` in `frontend/src/lib/types.ts`.
TAG_PALETTE = ("gray", "red", "orange", "yellow", "green", "blue", "purple", "pink")

DEFAULT_TAG_COLOR = TAG_PALETTE[0]


def get_tag_model() -> type:
    """Resolve Core's concrete `Tag` model via Django's app registry, the
    same lazy-resolution mechanism `get_catalog_entity_model()` uses. Only
    callable after `django.setup()` — from inside a function body, never
    cached at plugin module import time.
    """
    return _django_apps.get_model(TAG_LABEL)


def ensure_tags_exist(tags: list[str]) -> None:
    """`get_or_create` a `Tag` row for every tag string, defaulting new rows to the neutral color."""
    model = get_tag_model()
    for name in tags:
        model.objects.get_or_create(name=name)
