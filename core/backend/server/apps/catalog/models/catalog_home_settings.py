from django.db import models

DEFAULT_ABOUT_MARKDOWN = """\
Welcome to Atlas, your organization's software catalog. Atlas keeps track of \
the systems, components, APIs, resources, and teams that make up your \
architecture, and gives everyone a single place to find and understand them.

## Getting entities into the catalog

- **Register manually** — create a System, Component, API, or Resource by \
hand from the catalog UI when you just need something in the picture quickly.
- **Ingest from `catalog-info.yaml`** — connect a repository so Atlas keeps \
entities in sync automatically as the YAML changes.

## Learn more

See the [Getting Started guide]\
(https://sidorov-as.github.io/atlas/getting-started/) for a full walkthrough, \
including how each entity's documentation tab renders Markdown docs stored \
alongside its code.

Superusers can edit this section from **Settings → Home**.
"""


class CatalogHomeSettings(models.Model):
    """Singleton row backing the homepage's "About this catalog" section

    The codebase has no existing singleton-model convention to follow
    exactly, so this uses a fixed, well-known primary key (`SINGLETON_PK`)
    with a `get_solo()` accessor, kept as simple as `Tag`. Seeded via a
    `RunPython` data migration (0007_reset_tag_colors.py precedent) for a
    fresh deployment, but data migrations don't re-run on `manage.py flush`
    (`seed_booking_demo`'s own flush-and-repopulate step included) — so
    `get_solo()` also supplies `DEFAULT_ABOUT_MARKDOWN` as the `get_or_create`
    default, not just the migration, to guarantee real content on any first
    read of the singleton row, not only a genuinely fresh deployment. Always
    use `get_solo()` rather than querying this model directly.
    """

    SINGLETON_PK = 1

    about_markdown = models.TextField(blank=True)

    @classmethod
    def get_solo(cls) -> "CatalogHomeSettings":
        instance, _ = cls.objects.get_or_create(
            pk=cls.SINGLETON_PK,
            defaults={"about_markdown": DEFAULT_ABOUT_MARKDOWN},
        )
        return instance

    def __str__(self) -> str:
        return "Catalog Home Settings"
