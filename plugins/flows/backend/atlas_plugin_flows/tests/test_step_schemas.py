"""`StepIn` unit tests — pure Pydantic, no database: everything here is a
structural check `StepIn` itself can decide, as opposed to `test_flow_crud.py`
's/`test_flow_query_event_steps.py`'s full-stack HTTP tests covering what
only resolves against real data (ref resolution, the transition graph).
"""

import pytest
from pydantic import ValidationError

from atlas_plugin_flows.api.step_schemas import PositionIn, StepIn


def _errors(exc: ValidationError) -> list[str]:
    return [str(e["msg"]) for e in exc.value.errors()]


def test_minimal_step_is_valid():
    step = StepIn(id="a")

    assert step.id == "a"
    assert step.title is None


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError) as exc:
        StepIn(id="a", bogus_field="x")

    assert any("extra" in msg.lower() for msg in _errors(exc))


class TestIcon:
    def test_known_icon_name_is_accepted(self):
        step = StepIn(id="a", icon="CircleXmarkFill")

        assert step.icon == "CircleXmarkFill"

    def test_unknown_icon_name_is_rejected(self):
        with pytest.raises(ValidationError) as exc:
            StepIn(id="a", icon="NotARealIcon")

        assert any("not a known" in msg for msg in _errors(exc))


class TestColorAndLabelTheme:
    @pytest.mark.parametrize("field", ["color", "label_theme"])
    def test_known_value_is_accepted(self, field):
        step = StepIn(id="a", **{field: "danger"})

        assert getattr(step, field) == "danger"

    @pytest.mark.parametrize("field", ["color", "label_theme"])
    def test_unknown_value_is_rejected(self, field):
        with pytest.raises(ValidationError):
            StepIn(id="a", **{field: "chartreuse"})


class TestPosition:
    def test_valid_position_is_accepted(self):
        step = StepIn(id="a", position={"x": 1, "y": -2.5})

        assert step.position == PositionIn(x=1, y=-2.5)

    def test_boolean_coordinate_is_rejected(self):
        with pytest.raises(ValidationError):
            StepIn(id="a", position={"x": True, "y": 1})

    def test_missing_coordinate_is_rejected(self):
        with pytest.raises(ValidationError):
            StepIn(id="a", position={"x": 1})


class TestLinkUrl:
    def test_well_formed_http_url_is_accepted(self):
        step = StepIn(id="a", link_url="https://example.com/runbook")

        assert step.link_url == "https://example.com/runbook"

    def test_malformed_url_is_rejected(self):
        with pytest.raises(ValidationError) as exc:
            StepIn(id="a", link_url="not-a-url")

        assert any("well-formed" in msg for msg in _errors(exc))

    def test_javascript_scheme_is_rejected(self):
        with pytest.raises(ValidationError):
            StepIn(id="a", link_url="javascript:alert(1)")


class TestRefMutualExclusivity:
    def test_entity_ref_alone_is_valid(self):
        step = StepIn(id="a", entity_ref="component:checkout")

        assert step.entity_ref == "component:checkout"

    def test_entity_ref_and_link_url_together_is_rejected(self):
        with pytest.raises(ValidationError) as exc:
            StepIn(
                id="a",
                entity_ref="component:checkout",
                link_url="https://example.com",
            )

        assert any("more than one" in msg for msg in _errors(exc))

    def test_entity_ref_with_title_is_rejected(self):
        with pytest.raises(ValidationError) as exc:
            StepIn(id="a", entity_ref="component:checkout", title="Checkout")

        assert any("cannot also have" in msg for msg in _errors(exc))

    def test_entity_ref_with_explicit_null_title_is_accepted(self):
        step = StepIn(id="a", entity_ref="component:checkout", title=None)

        assert step.title is None

    def test_external_label_with_title_is_accepted(self):
        # Mirrors `models.py`'s own exclusion list exactly: only
        # entity_ref/query_ref/event_ref/flow_ref forbid title/summary —
        # external_label and link_url do not.
        step = StepIn(id="a", external_label="Legacy system", title="Legacy")

        assert step.title == "Legacy"


class TestSparseDump:
    def test_unset_optional_fields_are_excluded_from_dump(self):
        step = StepIn(
            id="a",
            query_ref={"api": "api:x", "endpoint": "e", "method": "GET", "path": "/x"},
        )

        dumped = step.model_dump(exclude_none=True)

        assert "summary" not in dumped["query_ref"]
        assert "position" not in dumped
        assert "icon" not in dumped
