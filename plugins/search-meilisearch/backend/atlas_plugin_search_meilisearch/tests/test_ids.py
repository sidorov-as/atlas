import pytest

from atlas_plugin_search_meilisearch.ids import (
    MAX_ENCODED_LENGTH,
    decode_id,
    encode_id,
)

AWKWARD = [
    "note:1",
    "api:payments/v1 beta",
    "kind:ключ-ü",
    "a_b:c_d",
    "a:b:c",
    "k:_",
    "k:_5f",
    "k:%/?#&=+",
]


@pytest.mark.parametrize("document_id", AWKWARD)
def test_encoded_ids_use_only_the_characters_the_engine_accepts(document_id):
    encoded = encode_id(document_id)
    assert encoded
    assert all(c.isascii() and (c.isalnum() or c in "-_") for c in encoded)


@pytest.mark.parametrize("document_id", AWKWARD)
def test_encoding_round_trips(document_id):
    assert decode_id(encode_id(document_id)) == document_id


def test_distinct_ids_stay_distinct():
    # `_5f` written out must not collide with an underscore.
    assert encode_id("k:_") != encode_id("k:_5f")
    assert len({encode_id(i) for i in AWKWARD}) == len(AWKWARD)


def test_an_overlong_id_falls_back_to_a_digest_that_cannot_clash():
    long_id = "note:" + "ü" * 500
    encoded = encode_id(long_id)
    assert len(encoded) <= MAX_ENCODED_LENGTH
    assert encoded == encode_id(long_id)
    assert encoded != encode_id(long_id + "x")
    assert encoded.startswith("_h")
    with pytest.raises(ValueError):
        decode_id(encoded)
