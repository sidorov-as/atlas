"""Startup orchestration tests (plugin-registries spec)."""

import logging

import django
import pytest

from server.apps.plugins import startup
from server.apps.plugins.composition import CompositionError
from server.apps.plugins.resolver import InvalidPluginDescriptorError


def test_bootstrap_logs_a_startup_summary_on_success(capsys):
    # `django.setup()` has already run for this test session (pytest-django);
    # calling it again here is a no-op, so this exercises the success path.
    # `django.setup()` reconfigures Django's LOGGING (structlog JSON to
    # stderr) on every call, which strips `caplog`'s root handler — read
    # the actual stderr output instead of relying on `caplog` here.
    startup.bootstrap()

    output = capsys.readouterr().err

    assert "Backend startup complete" in output
    assert "installed_apps=" in output
    assert "capability_ids=" in output
    assert "permission_ids=" in output
    assert "kind_ids=" in output


def test_bootstrap_exits_non_zero_on_a_composition_failure(monkeypatch, caplog):
    def _fail_setup(*args, **kwargs):
        raise CompositionError("duplicate id 'atlas.c4.diagram.read'")

    monkeypatch.setattr(django, "setup", _fail_setup)

    with (
        caplog.at_level(logging.ERROR, logger="server.apps.plugins"),
        pytest.raises(SystemExit) as exc_info,
    ):
        startup.bootstrap()

    assert exc_info.value.code == 1
    assert "composition" in caplog.text.lower()


def test_bootstrap_exits_non_zero_on_an_invalid_plugin_selection(
    monkeypatch,
    caplog,
):
    def _fail_setup(*args, **kwargs):
        raise InvalidPluginDescriptorError("bad descriptor")

    monkeypatch.setattr(django, "setup", _fail_setup)

    with (
        caplog.at_level(logging.ERROR, logger="server.apps.plugins"),
        pytest.raises(SystemExit) as exc_info,
    ):
        startup.bootstrap()

    assert exc_info.value.code == 1
    assert "invalid plugin selection" in caplog.text.lower()
