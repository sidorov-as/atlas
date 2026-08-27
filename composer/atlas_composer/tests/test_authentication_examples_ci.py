from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/authentication-examples-integration.yml"
CI_HELPER = REPO_ROOT / "examples/authentication/ci.py"
EXAMPLES = (
    "local",
    "oidc-keycloak",
    "oauth2-gitea",
    "custom-credentials",
)


def load_ci_helper() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "authentication_examples_ci", CI_HELPER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_integration_workflow_requires_every_topology_and_always_cleans_up() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    job = workflow["jobs"]["integration"]
    assert job["strategy"]["fail-fast"] is False
    assert tuple(job["strategy"]["matrix"]["example"]) == EXAMPLES
    assert "continue-on-error" not in job

    steps = {step["name"]: step for step in job["steps"] if "name" in step}
    assert steps["Start topology"]["run"].startswith("docker compose")
    assert "ci.py run" in steps["Run topology smoke test"]["run"]
    assert steps["Collect redacted diagnostics"]["if"] == "always()"
    assert "ci.py collect" in steps["Collect redacted diagnostics"]["run"]
    assert steps["Stop topology"]["if"] == "always()"
    assert "--volumes --remove-orphans" in steps["Stop topology"]["run"]
    assert steps["Upload redacted diagnostics"]["if"] == "always()"
    assert steps["Upload redacted diagnostics"]["with"]["retention-days"] == 7


def test_release_gate_covers_browser_and_security_negative_journeys() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    browser_job = workflow["jobs"]["integration"]
    negative_job = workflow["jobs"]["security-negative-journeys"]
    command = next(
        step["run"]
        for step in negative_job["steps"]
        if step.get("name") == "Run authentication security-negative journeys"
    )

    assert browser_job["name"].startswith("Release browser gate")
    assert tuple(browser_job["strategy"]["matrix"]["example"]) == EXAMPLES
    for required in (
        "test_admin_password_login_defaults_to_disabled",
        "test_inactive_principal_is_rejected_on_the_next_session_request",
        "test_source_fingerprint_change_requires_reviewed_migration",
        "test_restricted_policy_rejects_unverified_email_without_creating_state",
        "test_incomplete_exact_snapshot_rolls_back_and_failure_event_survives",
        "test_concurrent_first_login_creates_one_identity_and_actor",
        "test_legacy_oidc_grant_can_transfer_without_residual_manual_access",
        "test_membership_grant_migration.py",
    ):
        assert required in command


def test_ci_diagnostics_redact_declared_and_protocol_secrets() -> None:
    helper = load_ci_helper()
    raw = """Authorization: Bearer upstream-token
Cookie: sessionid=session-value; csrftoken=csrf-value
GITEA_CLIENT_SECRET=generated-secret
callback=/callback?code=oauth-code&state=oauth-state
payload={"password":"fixture-password","id_token":"eyJaaa.bbb.ccc"}
"""
    safe = helper.redact(
        raw,
        secrets=("upstream-token", "session-value", "fixture-password"),
    )

    for secret in (
        "upstream-token",
        "session-value",
        "csrf-value",
        "generated-secret",
        "oauth-code",
        "oauth-state",
        "fixture-password",
        "eyJaaa.bbb.ccc",
    ):
        assert secret not in safe
    assert "<redacted>" in safe
