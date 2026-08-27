"""Relation derivation contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard); `recompute_relations()`/
`entity_relations()` resolving against the real concrete model are covered
from Core's side (`core/backend/server/apps/catalog/tests/
test_plugin_contract_surface.py`).
"""

from atlas_plugin_api.catalog import KIND_ACTOR, KIND_COMPONENT, KIND_GROUP
from atlas_plugin_api.relations import _PREDICATE_PAIRS, RELATION_LABEL


def test_relation_label_matches_core_app_label():
    assert RELATION_LABEL == "catalog.Relation"


def test_predicate_pairs_cover_every_kind_that_derives_relations():
    assert _PREDICATE_PAIRS[KIND_COMPONENT] == [
        ("ownedBy", "ownerOf"),
        ("partOf", "hasPart"),
        ("dependsOn", "dependencyOf"),
        ("providesAPI", "apiProvidedBy"),
        ("consumesAPI", "apiConsumedBy"),
    ]
    assert _PREDICATE_PAIRS[KIND_GROUP] == [("hasMember", "memberOf")]
    assert _PREDICATE_PAIRS[KIND_ACTOR] == []


def test_relations_module_is_importable_without_django_setup():
    import atlas_plugin_api.relations  # noqa: F401
