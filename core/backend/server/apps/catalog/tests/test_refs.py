"""Ref parsing and case-insensitive uniqueness."""

import pytest
from django.db import IntegrityError, transaction

from server.apps.catalog import refs
from server.apps.catalog.tests.factories import create_resource

pytestmark = pytest.mark.django_db


def test_ref_without_namespace_resolves_to_default():
    assert refs.parse_ref("resource:user-db") == (
        "resource",
        "default",
        "user-db",
    )


def test_ref_with_explicit_namespace_is_parsed():
    assert refs.parse_ref("resource:team-a/user-db") == (
        "resource",
        "team-a",
        "user-db",
    )


def test_ref_without_kind_falls_back_to_default_kind():
    assert refs.parse_ref("user-db", default_kind="resource") == (
        "resource",
        "default",
        "user-db",
    )


def test_ref_without_kind_and_no_default_raises():
    with pytest.raises(refs.RefError):
        refs.parse_ref("user-db")


def test_resolve_ref_rejects_kind_mismatch(group):
    create_resource(name="primary-db", owner=group)
    with pytest.raises(refs.RefError):
        refs.resolve_ref("resource:primary-db", expected_kind="system")


def test_resolve_ref_is_case_insensitive_on_name_and_namespace(group):
    resource = create_resource(name="primary-db", owner=group)
    assert refs.resolve_ref("resource:PRIMARY-DB") == resource
    assert refs.resolve_ref("resource:default/primary-db") == resource


def test_case_different_name_collision_is_rejected(group):
    create_resource(name="auth", owner=group)

    with transaction.atomic(), pytest.raises(IntegrityError):
        create_resource(name="Auth", owner=group)


def test_same_name_different_namespace_does_not_collide(group):
    create_resource(name="auth", namespace="default", owner=group)
    other = create_resource(name="auth", namespace="team-a", owner=group)
    assert other.pk is not None
