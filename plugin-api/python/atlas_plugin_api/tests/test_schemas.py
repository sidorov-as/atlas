"""Shared CRUD API schema contract tests.

No Django settings are configured in this package's own test environment
(see `test_catalog.py`'s equivalent guard) — covers the Django-independent
schemas and validators only; `ref_validator`/`optional_ref_validator`/
`ref_list_validator` resolving a ref against the real concrete model are
exercised by every plugin's own CRUD API tests (they subclass these
validators to build their own `*SpecIn`/`*SpecPatch` schemas).
"""

import pytest
from pydantic import ValidationError

from atlas_plugin_api.refs import RefError
from atlas_plugin_api.schemas import (
    _DESCRIPTION_MAX_LENGTH,
    _DOCUMENTATION_MAX_LENGTH,
    _LABELS_MAX_ITEMS,
    _LINK_TITLE_MAX_LENGTH,
    _LINK_TYPE_MAX_LENGTH,
    _LINK_URL_MAX_LENGTH,
    _LINKS_MAX_ITEMS,
    _TAGS_MAX_ITEMS,
    AdoptIn,
    ArchitectureRelationshipDeclarationIn,
    CamelModel,
    EntityPath,
    LinkSchema,
    ListFilters,
    MetadataIn,
    MetadataOut,
    MetadataPatch,
    PageOut,
    PaginatedOut,
    RelationOut,
)


def test_camel_model_maps_snake_case_to_camel_case():
    class _Example(CamelModel):
        object_list: list[str]

    assert _Example.model_validate({"objectList": ["a"]}).object_list == ["a"]
    assert _Example(object_list=["a"]).model_dump(by_alias=True) == {
        "objectList": ["a"]
    }


def test_metadata_in_defaults():
    metadata = MetadataIn(name="checkout")
    assert metadata.title == ""
    assert metadata.labels == {}
    assert metadata.tags == []
    assert metadata.links == []


@pytest.mark.parametrize("name", ["", "   ", "checkout/api", "checkout:api"])
def test_metadata_in_rejects_invalid_name(name):
    with pytest.raises(ValidationError):
        MetadataIn(name=name)


def test_metadata_in_strips_surrounding_whitespace_from_name():
    assert MetadataIn(name=" checkout ").name == "checkout"


@pytest.mark.parametrize("name", ["", "   ", "checkout/api", "checkout:api"])
def test_metadata_patch_rejects_explicit_invalid_name(name):
    with pytest.raises(ValidationError):
        MetadataPatch(name=name)


def test_metadata_patch_omitted_name_is_not_validated_or_set():
    patch = MetadataPatch(title="Checkout")
    assert "name" not in patch.model_fields_set
    assert patch.name is None


def test_link_description_defaults_for_legacy_links():
    assert (
        LinkSchema(
            url="https://docs.example.test", title="Docs", type="wiki"
        ).description
        == ""
    )


def test_metadata_patch_leaves_unset_fields_out_of_model_fields_set():
    patch = MetadataPatch(name="checkout")
    assert patch.model_fields_set == {"name"}


def test_metadata_out_serializes_camel_case():
    out = MetadataOut(
        name="checkout",
        title="",
        description="",
        documentation="",
        labels={},
        tags=[],
        links=[],
    )
    assert out.model_dump(by_alias=True)["tagColors"] == {}


def test_page_out_and_paginated_out_serialize_camel_case():
    page = PageOut[str](number=1, object_list=["a", "b"])
    assert page.model_dump(by_alias=True) == {"number": 1, "objectList": ["a", "b"]}

    paginated = PaginatedOut[str](count=2, num_pages=1, per_page=20, page=page)
    dumped = paginated.model_dump(by_alias=True)
    assert dumped["numPages"] == 1
    assert dumped["perPage"] == 20


def test_relation_out_and_entity_path_and_adopt_in_are_plain_camel_models():
    RelationOut(
        predicate="ownedBy",
        target="group:platform",
        target_kind="group",
        target_id="11111111-1111-1111-1111-111111111111",
        status="active",
        deprecated=False,
    )
    EntityPath(id="11111111-1111-1111-1111-111111111111")
    assert AdoptIn(repository="org/repo").repository == "org/repo"


def test_list_filters_defaults_and_forced_list_fields():
    filters = ListFilters()
    assert filters.page == 1
    assert filters.sort == "name"
    assert "tags" in ListFilters.__dmr_force_list__


def test_architecture_relationship_declaration_in_validates_target_syntax():
    ArchitectureRelationshipDeclarationIn(
        target="component:checkout-api", label="calls"
    )

    with pytest.raises(ValidationError):
        # No `kind:` prefix and no default kind to infer one from.
        ArchitectureRelationshipDeclarationIn(target="checkout-api", label="calls")


def test_ref_error_is_a_value_error():
    assert issubclass(RefError, ValueError)


def test_schemas_module_is_importable_without_django_setup():
    import atlas_plugin_api.schemas  # noqa: F401


@pytest.mark.parametrize("model_cls", [MetadataIn, MetadataPatch])
def test_metadata_rejects_oversized_description(model_cls):
    kwargs = {"name": "checkout"} if model_cls is MetadataIn else {}
    with pytest.raises(ValidationError):
        model_cls(description="x" * (_DESCRIPTION_MAX_LENGTH + 1), **kwargs)


@pytest.mark.parametrize("model_cls", [MetadataIn, MetadataPatch])
def test_metadata_rejects_oversized_documentation(model_cls):
    kwargs = {"name": "checkout"} if model_cls is MetadataIn else {}
    with pytest.raises(ValidationError):
        model_cls(documentation="x" * (_DOCUMENTATION_MAX_LENGTH + 1), **kwargs)


@pytest.mark.parametrize("model_cls", [MetadataIn, MetadataPatch])
def test_metadata_rejects_too_many_labels(model_cls):
    kwargs = {"name": "checkout"} if model_cls is MetadataIn else {}
    labels = {f"key{i}": "value" for i in range(_LABELS_MAX_ITEMS + 1)}
    with pytest.raises(ValidationError):
        model_cls(labels=labels, **kwargs)


@pytest.mark.parametrize("model_cls", [MetadataIn, MetadataPatch])
def test_metadata_rejects_too_many_tags(model_cls):
    kwargs = {"name": "checkout"} if model_cls is MetadataIn else {}
    tags = [f"tag{i}" for i in range(_TAGS_MAX_ITEMS + 1)]
    with pytest.raises(ValidationError):
        model_cls(tags=tags, **kwargs)


@pytest.mark.parametrize("model_cls", [MetadataIn, MetadataPatch])
def test_metadata_rejects_too_many_links(model_cls):
    kwargs = {"name": "checkout"} if model_cls is MetadataIn else {}
    links = [{"url": "https://example.test"} for _ in range(_LINKS_MAX_ITEMS + 1)]
    with pytest.raises(ValidationError):
        model_cls(links=links, **kwargs)


@pytest.mark.parametrize("model_cls", [MetadataIn, MetadataPatch])
@pytest.mark.parametrize(
    ("field", "max_length"),
    [
        ("url", _LINK_URL_MAX_LENGTH),
        ("title", _LINK_TITLE_MAX_LENGTH),
        ("description", _DESCRIPTION_MAX_LENGTH),
        ("type", _LINK_TYPE_MAX_LENGTH),
    ],
)
def test_metadata_rejects_oversized_link_field(model_cls, field, max_length):
    kwargs = {"name": "checkout"} if model_cls is MetadataIn else {}
    link = {"url": "https://example.test", field: "x" * (max_length + 1)}
    with pytest.raises(ValidationError):
        model_cls(links=[link], **kwargs)


def test_link_schema_rejects_oversized_fields_directly():
    with pytest.raises(ValidationError):
        LinkSchema(url="x" * (_LINK_URL_MAX_LENGTH + 1))
