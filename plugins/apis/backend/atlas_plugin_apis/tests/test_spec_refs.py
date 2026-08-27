"""Tests for `atlas_plugin_apis.spec_refs.resolve_schema` in isolation
no Django/DB fixtures needed, this module
is a pure function over plain dicts/lists."""

from atlas_plugin_apis.spec_refs import resolve_schema

# --- basic resolution ---------------------------------------------------


def test_bare_top_level_ref_resolves_to_expanded_content():
    spec = {
        "components": {
            "schemas": {
                "User": {"type": "object", "properties": {"id": {"type": "string"}}}
            }
        }
    }
    node = {"$ref": "#/components/schemas/User"}

    assert resolve_schema(node, spec) == {
        "type": "object",
        "properties": {"id": {"type": "string"}},
    }


def test_ref_nested_inside_a_property_resolves():
    spec = {
        "components": {
            "schemas": {
                "Money": {
                    "type": "object",
                    "properties": {"amount": {"type": "number"}},
                }
            }
        }
    }
    node = {
        "type": "object",
        "properties": {"price": {"$ref": "#/components/schemas/Money"}},
    }

    resolved = resolve_schema(node, spec)

    assert resolved["properties"]["price"] == {
        "type": "object",
        "properties": {"amount": {"type": "number"}},
    }


def test_ref_chain_fully_resolves():
    spec = {
        "components": {
            "schemas": {
                "A": {"$ref": "#/components/schemas/B"},
                "B": {"type": "string"},
            }
        }
    }
    node = {"$ref": "#/components/schemas/A"}

    assert resolve_schema(node, spec) == {"type": "string"}


def test_fragment_pointer_is_normalized_and_resolves():
    spec = {"components": {"schemas": {"User": {"type": "object"}}}}
    node = {"$ref": "#/components/schemas/User"}

    assert resolve_schema(node, spec) == {"type": "object"}


# --- cycle safety ---------------------------------------------------------


def test_self_referential_schema_stops_at_the_cycle():
    spec = {
        "components": {
            "schemas": {
                "Category": {
                    "type": "object",
                    "properties": {
                        "children": {"$ref": "#/components/schemas/Category"}
                    },
                }
            }
        }
    }
    node = {"$ref": "#/components/schemas/Category"}

    resolved = resolve_schema(node, spec)

    assert resolved["properties"]["children"] == {
        "$ref": "#/components/schemas/Category"
    }


def test_two_independent_branches_referencing_the_same_schema_both_resolve_fully():
    spec = {
        "components": {
            "schemas": {
                "Money": {
                    "type": "object",
                    "properties": {"amount": {"type": "number"}},
                }
            }
        }
    }
    node = {
        "type": "object",
        "properties": {
            "price": {"$ref": "#/components/schemas/Money"},
            "refund": {"$ref": "#/components/schemas/Money"},
        },
    }

    resolved = resolve_schema(node, spec)

    money = {"type": "object", "properties": {"amount": {"type": "number"}}}
    assert resolved["properties"]["price"] == money
    assert resolved["properties"]["refund"] == money


# --- dangling refs ---------------------------------------------------------


def test_dangling_ref_is_left_unresolved_without_raising():
    spec = {"components": {"schemas": {}}}
    node = {"$ref": "#/components/schemas/Missing"}

    assert resolve_schema(node, spec) == {"$ref": "#/components/schemas/Missing"}


# --- schema-aware walk scoping ---------------------------------------------


def test_ref_inside_example_default_enum_const_is_never_touched():
    spec = {"components": {"schemas": {"User": {"type": "object"}}}}
    node = {
        "type": "object",
        "example": {"$ref": "not-a-reference"},
        "examples": [{"payload": {"$ref": "not-a-reference"}}],
        "default": {"$ref": "not-a-reference"},
        "enum": [{"$ref": "not-a-reference"}],
        "const": {"$ref": "not-a-reference"},
    }

    resolved = resolve_schema(node, spec)

    assert resolved["example"] == {"$ref": "not-a-reference"}
    assert resolved["examples"] == [{"payload": {"$ref": "not-a-reference"}}]
    assert resolved["default"] == {"$ref": "not-a-reference"}
    assert resolved["enum"] == [{"$ref": "not-a-reference"}]
    assert resolved["const"] == {"$ref": "not-a-reference"}


# --- merge_siblings=True ----------------------------------------------------


def test_merge_siblings_true_overlays_sibling_on_resolved_target():
    spec = {
        "components": {
            "schemas": {
                "Booking": {"type": "object", "properties": {"id": {"type": "string"}}}
            }
        }
    }
    node = {"$ref": "#/components/schemas/Booking", "description": "override"}

    resolved = resolve_schema(node, spec, merge_siblings=True)

    assert resolved == {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "description": "override",
    }


def test_merge_siblings_true_sibling_collision_wins_over_target():
    spec = {
        "components": {
            "schemas": {"Booking": {"type": "object", "description": "original"}}
        }
    }
    node = {"$ref": "#/components/schemas/Booking", "description": "override"}

    resolved = resolve_schema(node, spec, merge_siblings=True)

    assert resolved["description"] == "override"


def test_merge_siblings_true_sibling_value_with_its_own_ref_is_resolved_before_overlay():
    spec = {
        "components": {
            "schemas": {
                "Booking": {"type": "object"},
                "CancelledBooking": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}},
                },
            }
        }
    }
    node = {
        "$ref": "#/components/schemas/Booking",
        "not": {"$ref": "#/components/schemas/CancelledBooking"},
    }

    resolved = resolve_schema(node, spec, merge_siblings=True)

    assert resolved["not"] == {
        "type": "object",
        "properties": {"reason": {"type": "string"}},
    }


def test_merge_siblings_true_sibling_survives_a_cycle():
    spec = {
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "properties": {
                        "self": {
                            "$ref": "#/components/schemas/A",
                            "description": "override",
                        },
                    },
                },
            }
        }
    }
    node = {"$ref": "#/components/schemas/A"}

    resolved = resolve_schema(node, spec, merge_siblings=True)

    cycle_node = resolved["properties"]["self"]
    assert cycle_node == {"$ref": "#/components/schemas/A", "description": "override"}


def test_merge_siblings_true_sibling_survives_a_dangling_ref():
    spec = {"components": {"schemas": {}}}
    node = {"$ref": "#/components/schemas/Missing", "description": "override"}

    resolved = resolve_schema(node, spec, merge_siblings=True)

    assert resolved == {
        "$ref": "#/components/schemas/Missing",
        "description": "override",
    }


# --- merge_siblings=False (default) -----------------------------------------


def test_merge_siblings_false_resolves_without_attaching_sibling():
    spec = {
        "components": {
            "schemas": {
                "Booking": {"type": "object", "properties": {"id": {"type": "string"}}}
            }
        }
    }
    node = {"$ref": "#/components/schemas/Booking", "description": "override"}

    resolved = resolve_schema(node, spec, merge_siblings=False)

    assert resolved == {"type": "object", "properties": {"id": {"type": "string"}}}


def test_merge_siblings_false_cycle_drops_sibling():
    spec = {
        "components": {
            "schemas": {
                "A": {
                    "type": "object",
                    "properties": {
                        "self": {
                            "$ref": "#/components/schemas/A",
                            "description": "override",
                        },
                    },
                },
            }
        }
    }
    node = {"$ref": "#/components/schemas/A"}

    resolved = resolve_schema(node, spec, merge_siblings=False)

    cycle_node = resolved["properties"]["self"]
    assert cycle_node == {"$ref": "#/components/schemas/A"}


def test_merge_siblings_false_dangling_drops_sibling():
    spec = {"components": {"schemas": {}}}
    node = {"$ref": "#/components/schemas/Missing", "description": "override"}

    resolved = resolve_schema(node, spec, merge_siblings=False)

    assert resolved == {"$ref": "#/components/schemas/Missing"}
