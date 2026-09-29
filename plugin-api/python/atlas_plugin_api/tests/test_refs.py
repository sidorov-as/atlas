"""Ref-string parser/resolver contract tests."""

import pytest

from atlas_plugin_api.refs import DEFAULT_NAMESPACE, RefError, parse_ref


def test_parse_ref_with_explicit_kind_and_namespace():
    assert parse_ref("system:default/checkout") == ("system", "default", "checkout")


def test_parse_ref_defaults_namespace():
    assert parse_ref("component:checkout-api") == (
        "component",
        DEFAULT_NAMESPACE,
        "checkout-api",
    )


def test_parse_ref_uses_default_kind_when_none_given():
    assert parse_ref("checkout", default_kind="group") == (
        "group",
        DEFAULT_NAMESPACE,
        "checkout",
    )


def test_parse_ref_rejects_a_ref_with_no_kind_and_no_default():
    with pytest.raises(RefError):
        parse_ref("checkout")


def test_parse_ref_rejects_an_empty_ref():
    with pytest.raises(RefError):
        parse_ref("")


def test_refs_module_is_importable_without_django_setup():
    import atlas_plugin_api.refs  # noqa: F401
