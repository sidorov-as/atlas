"""List-endpoint filtering contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard) — a stub queryset stands in for
the real Django `QuerySet` since none of this module's logic touches the
database itself, only builds `.filter(**kwargs)` calls.
"""

import pytest
from dmr.response import APIError

from atlas_plugin_api.filters import (
    filter_by_field,
    filter_by_owner,
    filter_by_search,
    filter_by_system,
    filter_by_tags_overlap,
    filter_by_team,
)


class _StubQuerySet:
    def __init__(self, calls=None):
        self.calls = calls if calls is not None else []

    def filter(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self


def test_filter_by_owner_passes_through_when_empty():
    queryset = _StubQuerySet()
    assert filter_by_owner(queryset, None) is queryset
    assert queryset.calls == []


def test_filter_by_owner_filters_by_parsed_namespace_and_name():
    queryset = _StubQuerySet()
    filter_by_owner(queryset, "platform-team")
    assert queryset.calls == [
        ((), {"owner__namespace": "default", "owner__name__iexact": "platform-team"})
    ]


def test_filter_by_owner_rejects_an_invalid_ref():
    with pytest.raises(APIError):
        filter_by_owner(_StubQuerySet(), "bad/ref/too/many/slashes:x")


def test_filter_by_system_uses_the_given_prefix():
    queryset = _StubQuerySet()
    filter_by_system(queryset, "checkout", prefix="component_details__")
    assert queryset.calls == [
        (
            (),
            {
                "component_details__system__namespace": "default",
                "component_details__system__name__iexact": "checkout",
            },
        )
    ]


def test_filter_by_team_filters_through_system_owner():
    queryset = _StubQuerySet()
    filter_by_team(queryset, "platform-team")
    assert queryset.calls == [
        (
            (),
            {
                "system__owner__namespace": "default",
                "system__owner__name__iexact": "platform-team",
            },
        )
    ]


def test_filter_by_field_passes_through_when_empty():
    queryset = _StubQuerySet()
    assert filter_by_field(queryset, "lifecycle", None) is queryset


def test_filter_by_field_filters_by_the_given_field_and_prefix():
    queryset = _StubQuerySet()
    filter_by_field(queryset, "lifecycle", "production", prefix="component_details__")
    assert queryset.calls == [((), {"component_details__lifecycle": "production"})]


def test_filter_by_search_passes_through_when_empty():
    queryset = _StubQuerySet()
    assert filter_by_search(queryset, None) is queryset


def test_filter_by_search_filters():
    queryset = _StubQuerySet()
    filter_by_search(queryset, "checkout")
    assert len(queryset.calls) == 1


def test_filter_by_tags_overlap_passes_through_when_empty():
    queryset = _StubQuerySet()
    assert filter_by_tags_overlap(queryset, []) is queryset


def test_filter_by_tags_overlap_filters():
    queryset = _StubQuerySet()
    filter_by_tags_overlap(queryset, ["payments"])
    assert queryset.calls == [((), {"tags__overlap": ["payments"]})]


def test_filters_module_is_importable_without_django_setup():
    import atlas_plugin_api.filters  # noqa: F401
