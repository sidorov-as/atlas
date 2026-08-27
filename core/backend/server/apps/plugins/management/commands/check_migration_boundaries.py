"""`manage.py check_migration_boundaries`.

A plugin's migrations may declare `dependencies` only on Core's migrations
and its own prior migration history (plugin-architecture.md:560) — never on
another plugin's migrations or models. A cross-plugin migration dependency
would make the depended-on plugin un-removable (its migration table can't be
unapplied/absent without breaking the dependent plugin's graph), defeating
the whole point of `disabled`/`removed` being safe, data-preserving states.

Core is exempt: it's not "a plugin" for purposes of this rule, and its own
migration history already, deliberately, depends on `ingestion` (e.g.
`catalog.0001_initial`, `catalog.0012_catalog_entity_identity`, for
`CatalogEntity.ingested_from`) — a pre-existing, one-directional dependency
this check doesn't second-guess.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand, CommandError
from django.db.migrations.loader import MigrationLoader

from server.apps.plugins.resolver import load_selected_descriptors
from server.settings.selected_plugins import SELECTED_PLUGINS

if TYPE_CHECKING:
    from django.db.migrations import Migration

CORE_PLUGIN_ID = "atlas.catalog"


class Command(BaseCommand):
    help = (
        "Check that each plugin's migrations depend only on Core's "
        "migrations and their own prior migration history, never another "
        "plugin's."
    )

    def handle(self, *args, **options) -> None:
        violations = _find_violations(_plugin_by_app_label())

        if violations:
            raise CommandError(
                "Cross-plugin migration dependency found:\n"
                + "\n".join(f"  - {violation}" for violation in violations),
            )

        self.stdout.write(
            self.style.SUCCESS(
                "No cross-plugin migration dependencies found.",
            )
        )


def _plugin_by_app_label() -> dict[str, str]:
    """Map each plugin-owned Django app label to its owning plugin id."""
    configs_by_name = {
        config.name: config for config in django_apps.get_app_configs()
    }
    mapping: dict[str, str] = {}
    for descriptor in load_selected_descriptors(SELECTED_PLUGINS):
        for app_name in descriptor.django_apps:
            app_config = configs_by_name.get(app_name)
            if app_config is not None:
                mapping[app_config.label] = descriptor.id
    return mapping


def _violation_for(
    app_label: str,
    migration_name: str,
    dependencies: Iterable[tuple[str, str]],
    plugin_by_app_label: dict[str, str],
) -> str | None:
    """Check one migration's `dependencies` against the ownership map.

    Returns a human-readable violation message, or None if the migration's
    dependencies stay within its own plugin (or point at Core/an unmapped
    app, both of which are allowed).
    """
    owner = plugin_by_app_label.get(app_label)
    if owner is None or owner == CORE_PLUGIN_ID:
        return None  # not a plugin-owned app, or Core itself (exempt)

    for dependency in dependencies:
        dep_app_label = dependency[0]
        if dep_app_label == app_label:
            continue  # own history

        dep_owner = plugin_by_app_label.get(dep_app_label)
        if dep_owner is None or dep_owner == CORE_PLUGIN_ID:
            continue  # Core or an unmapped app — always an allowed target

        if dep_owner != owner:
            dep_name = dependency[1]
            return (
                f"{app_label}.{migration_name} (plugin {owner!r}) depends "
                f"on {dep_app_label}.{dep_name} (plugin {dep_owner!r}) — a "
                "plugin's migrations may only depend on Core and its own "
                "history."
            )

    return None


def _find_violations(
    plugin_by_app_label: dict[str, str],
    migrations: dict[tuple[str, str], Migration] | None = None,
) -> list[str]:
    if migrations is None:
        loader = MigrationLoader(None, load=False)
        loader.load_disk()
        migrations = loader.disk_migrations

    violations = []
    for (app_label, name), migration in sorted(migrations.items()):
        violation = _violation_for(
            app_label,
            name,
            migration.dependencies,
            plugin_by_app_label,
        )
        if violation is not None:
            violations.append(violation)
    return violations
