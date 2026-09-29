from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import validate_docs


class SourceContractTests(unittest.TestCase):
    def test_provider_ids_routes_and_schema_fields_come_from_source(self) -> None:
        self.assertEqual(
            validate_docs.source_provider_ids(),
            {
                "atlas.auth.local",
                "atlas.auth.oidc",
                "atlas.auth.gitea",
            },
        )
        self.assertIn(
            "/auth/browser/v1/providers/{provider_id}/callback",
            validate_docs.source_gateway_routes(),
        )
        manifest_fields = validate_docs.source_manifest_fields()
        self.assertIn("sessionMaxAgeSeconds", manifest_fields["auth"])
        self.assertIn("principalProvisioning", manifest_fields["provider"])
        self.assertIn(
            "discoveryUrl",
            validate_docs.source_provider_config_fields()["atlas.auth.oidc"],
        )

    def test_checked_in_auth_navigation_matches_contract(self) -> None:
        errors: list[str] = []
        validate_docs.validate_navigation(errors)
        self.assertEqual(errors, [])


class DocumentationDriftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "guide.md"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_unknown_provider_environment_and_callback_are_rejected(self) -> None:
        self.path.write_text(
            "Use `atlas.auth.typo` with `ATLAS_UNKNOWN_SECRET` and "
            "`/auth/browser/v1/providers/atlas.auth.typo/callback`."
        )
        errors: list[str] = []
        validate_docs.validate_source_references(
            errors,
            [self.path],
            {"atlas.auth.local"},
            {"ATLAS_KNOWN_SECRET"},
            validate_docs.source_gateway_routes(),
        )
        self.assertTrue(
            any("provider id 'atlas.auth.typo'" in error for error in errors)
        )
        self.assertTrue(any("ATLAS_UNKNOWN_SECRET" in error for error in errors))
        self.assertTrue(any("gateway route" in error for error in errors))

    def test_manifest_and_provider_config_drift_are_rejected(self) -> None:
        self.path.write_text(
            """```yaml
auth:
  providers:
    - id: atlas.auth.oidc
      principalProvisioning: automatic
      removedPolicy: true
  default: atlas.auth.oidc
plugins:
  - id: atlas.auth.oidc
    config:
      discoveryUrl: https://idp.example/.well-known/openid-configuration
      removedField: true
```
"""
        )
        errors: list[str] = []
        validate_docs.validate_yaml_snippets(
            errors,
            [self.path],
            validate_docs.source_manifest_fields(),
            validate_docs.source_provider_ids(),
            validate_docs.source_provider_config_fields(),
        )
        self.assertTrue(any("removedPolicy" in error for error in errors))
        self.assertTrue(any("removedField" in error for error in errors))

    def test_broken_relative_link_is_rejected(self) -> None:
        self.path.write_text("Read [the missing guide](missing.md).")
        errors: list[str] = []
        validate_docs.validate_links(errors, [self.path])
        self.assertEqual(len(errors), 1)
        self.assertIn("does not exist", errors[0])


if __name__ == "__main__":
    unittest.main()
