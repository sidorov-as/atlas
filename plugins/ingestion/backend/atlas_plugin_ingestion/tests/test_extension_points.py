"""Unit tests for `KeyedExtensionPoint`, exercised through the
`facet_writers` extension point
— registration, resolution, duplicate-key rejection, and the "nothing
registered" no-op `connectors`/`parsers` already rely on.
"""

import pytest

from atlas_plugin_ingestion.extension_points import (
    DuplicateExtensionPointRegistrationError,
    KeyedExtensionPoint,
)


def test_resolve_returns_none_when_nothing_is_registered():
    point = KeyedExtensionPoint("test.point.v1")

    assert point.resolve("database-schema") is None


def test_register_then_resolve_returns_the_same_implementation():
    point = KeyedExtensionPoint("test.point.v1")
    implementation = object()

    point.register("database-schema", implementation)

    assert point.resolve("database-schema") is implementation


def test_registering_the_same_key_twice_raises():
    point = KeyedExtensionPoint("test.point.v1")
    point.register("database-schema", object())

    with pytest.raises(DuplicateExtensionPointRegistrationError):
        point.register("database-schema", object())


def test_registered_keys_lists_every_registered_key_sorted():
    point = KeyedExtensionPoint("test.point.v1")
    point.register("zzz", object())
    point.register("aaa", object())

    assert point.registered_keys() == ["aaa", "zzz"]


def test_resolving_an_unregistered_key_is_a_no_op_alongside_others():
    point = KeyedExtensionPoint("test.point.v1")
    point.register("database-schema", object())

    assert point.resolve("something-else") is None
