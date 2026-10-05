"""Reversible mapping from search document ids to Meilisearch identifiers.

Meilisearch accepts only letters, digits, `-` and `_` in a document id and at
most 511 bytes. Search ids look like `kind:key`, so every other byte is
written as `_` plus two hex digits (and `_` itself as `_5f`). The mapping is
injective, which keeps distinct ids distinct, and `decode_id` inverts it.

An id whose encoding would not fit falls back to `_h` plus a SHA-256 digest.
That form cannot clash with an encoded id (`h` is not a hex digit after the
`_`) and is not invertible, so the adapter also stores the original id in a
field and returns that, never the decoded identifier.
"""

import hashlib

MAX_ENCODED_LENGTH = 400

_SAFE = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-")
_HASH_PREFIX = "_h"


def encode_id(document_id: str) -> str:
    raw = document_id.encode("utf-8")
    encoded = "".join(chr(b) if b in _SAFE else f"_{b:02x}" for b in raw)
    if len(encoded) <= MAX_ENCODED_LENGTH:
        return encoded
    return _HASH_PREFIX + hashlib.sha256(raw).hexdigest()


def decode_id(encoded: str) -> str:
    if encoded.startswith(_HASH_PREFIX):
        raise ValueError("hashed ids cannot be decoded; read the stored original")
    out = bytearray()
    index = 0
    while index < len(encoded):
        char = encoded[index]
        if char == "_":
            out.append(int(encoded[index + 1 : index + 3], 16))
            index += 3
        else:
            out.append(ord(char))
            index += 1
    return out.decode("utf-8")
