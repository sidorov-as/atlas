"""Migration linter wiring.

`django_safe_migrations` (already a dev dependency, wired into
`INSTALLED_APPS` in `environments/development.py`) supplies the actual rule
engine; these tests exercise *our* configuration of it — that a destructive
operation is blocking by default and that the library's own
`# safe-migrations: ignore ...` suppression comment is the "explicit
maintenance-mode marker with a justification" the lint calls for — plus
the cross-plugin migration-dependency check, which has no off-the-shelf
equivalent and is entirely bespoke (`check_migration_boundaries`).
"""

from __future__ import annotations

import importlib
import sys
import textwrap

from django_safe_migrations.analyzer import MigrationAnalyzer
from django_safe_migrations.conf import get_warnings_as_errors
from django_safe_migrations.rules.alter_field import AlterFieldNullFalseRule
from django_safe_migrations.rules.base import Severity

from server.apps.plugins.management.commands.check_migration_boundaries import (
    _find_violations,
    _violation_for,
)

DESTRUCTIVE_REMOVE_FIELD = """
    from django.db import migrations

    class Migration(migrations.Migration):
        dependencies = []
        operations = [
            migrations.RemoveField(model_name='widget', name='legacy_field'),
        ]
    """

DESTRUCTIVE_DELETE_MODEL = """
    from django.db import migrations

    class Migration(migrations.Migration):
        dependencies = []
        operations = [
            migrations.DeleteModel(name='Widget'),
        ]
    """

SUPPRESSED_REMOVE_FIELD = """
    from django.db import migrations

    class Migration(migrations.Migration):
        dependencies = []
        operations = [
            # safe-migrations: ignore SM002 -- maintenance-mode: dead column
            migrations.RemoveField(model_name='widget', name='legacy_field'),
        ]
    """


def _load_migration(tmp_path, monkeypatch, source: str, module_name: str):
    """Write *source* as a real module on disk and instantiate its `Migration`.

    A real file (not an in-memory object) is required: suppression-comment
    lookup and operation-line resolution both re-read the migration's source
    file by path, so the synthetic migration needs one to be a faithful
    stand-in for a real destructive migration.
    """
    (tmp_path / f"{module_name}.py").write_text(textwrap.dedent(source))
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    return module.Migration("0002_test", "testapp")


def test_destructive_rules_are_promoted_to_blocking():
    # SM002 (RemoveField) / SM003 (DeleteModel) ship as WARNING severity
    # upstream; our config promotes them so a plain `django-safe-migrations`
    # warning actually fails CI, per the "blocked outside maintenance mode"
    # requirement.
    assert {"SM002", "SM003"} <= set(get_warnings_as_errors())


def test_nullability_narrowing_is_already_blocking_by_default():
    # AlterField narrowing null=True -> null=False needs no promotion: it's
    # ERROR severity upstream already.
    assert AlterFieldNullFalseRule.severity == Severity.ERROR


def test_remove_field_migration_is_flagged(tmp_path, monkeypatch):
    migration = _load_migration(
        tmp_path,
        monkeypatch,
        DESTRUCTIVE_REMOVE_FIELD,
        "remove_field_mig",
    )

    issues = MigrationAnalyzer().analyze_migration(
        migration,
        app_label="testapp",
        migration_name="0002_test",
    )

    assert "SM002" in {issue.rule_id for issue in issues}


def test_delete_model_migration_is_flagged(tmp_path, monkeypatch):
    migration = _load_migration(
        tmp_path,
        monkeypatch,
        DESTRUCTIVE_DELETE_MODEL,
        "delete_model_mig",
    )

    issues = MigrationAnalyzer().analyze_migration(
        migration,
        app_label="testapp",
        migration_name="0002_test",
    )

    assert "SM003" in {issue.rule_id for issue in issues}


def test_explicitly_marked_migration_is_allowed(tmp_path, monkeypatch):
    migration = _load_migration(
        tmp_path,
        monkeypatch,
        SUPPRESSED_REMOVE_FIELD,
        "suppressed_mig",
    )

    issues = MigrationAnalyzer().analyze_migration(
        migration,
        app_label="testapp",
        migration_name="0002_test",
    )

    assert "SM002" not in {issue.rule_id for issue in issues}


# -- Cross-plugin migration dependency check ----------------------


PLUGIN_A = "atlas.plugin-a"
PLUGIN_B = "atlas.plugin-b"
CORE = "atlas.catalog"
OWNERS = {"app_a": PLUGIN_A, "app_b": PLUGIN_B, "catalog": CORE}


class _FakeMigration:
    def __init__(self, dependencies):
        self.dependencies = dependencies


def test_dependency_on_another_plugin_is_a_violation():
    violation = _violation_for(
        "app_a",
        "0002_bad",
        [("app_b", "0001_initial")],
        OWNERS,
    )

    assert violation is not None
    assert "app_a.0002_bad" in violation
    assert PLUGIN_B in violation


def test_dependency_on_core_is_allowed():
    assert (
        _violation_for(
            "app_a",
            "0002_ok",
            [("catalog", "0001_initial")],
            OWNERS,
        )
        is None
    )


def test_dependency_on_own_history_is_allowed():
    assert (
        _violation_for(
            "app_a",
            "0002_ok",
            [("app_a", "0001_initial")],
            OWNERS,
        )
        is None
    )


def test_core_depending_on_a_plugin_is_exempt():
    # Mirrors the real repo: `catalog` depends on `ingestion` for
    # `CatalogEntity.ingested_from` — Core isn't "a plugin" for this rule.
    assert (
        _violation_for(
            "catalog",
            "0001_initial",
            [("app_a", "0001_initial")],
            OWNERS,
        )
        is None
    )


def test_find_violations_collects_across_migrations():
    migrations = {
        ("app_a", "0001_initial"): _FakeMigration([]),
        ("app_a", "0002_bad"): _FakeMigration([("app_b", "0001_initial")]),
        ("app_b", "0001_initial"): _FakeMigration([]),
        ("catalog", "0001_initial"): _FakeMigration(
            [("app_a", "0001_initial")]
        ),
    }

    violations = _find_violations(OWNERS, migrations)

    assert len(violations) == 1
    assert "app_a.0002_bad" in violations[0]


def test_no_cross_plugin_dependencies_in_the_real_migration_history():
    from server.apps.plugins.management.commands import (
        check_migration_boundaries as cmd,
    )

    assert _find_violations(cmd._plugin_by_app_label()) == []
