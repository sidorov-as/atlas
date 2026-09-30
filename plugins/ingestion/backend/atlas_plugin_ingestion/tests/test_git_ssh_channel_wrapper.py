"""`_ParamikoChannelWrapper.read` must honour file-like `read(n)` semantics.

`paramiko.Channel.recv` returns however many bytes have arrived, but dulwich
expects `read(n)` to return exactly `n` bytes unless the stream ended.
"""

import pytest

from atlas_plugin_ingestion.connectors.git import _ParamikoChannelWrapper


class _FakeChannel:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def recv(self, n: int) -> bytes:
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        if len(chunk) > n:
            self._chunks.insert(0, chunk[n:])
            chunk = chunk[:n]
        return chunk


def _wrapper(chunks: list[bytes]) -> _ParamikoChannelWrapper:
    return _ParamikoChannelWrapper(None, _FakeChannel(chunks))  # type: ignore[arg-type]


def test_read_reassembles_short_recv_results():
    assert _wrapper([b"0", b"0", b"0", b"6x"]).read(5) == b"0006x"[:5]


def test_read_returns_partial_data_at_eof():
    assert _wrapper([b"ab"]).read(5) == b"ab"


def test_read_raises_when_stream_is_closed_with_no_data():
    with pytest.raises(ConnectionError):
        _wrapper([]).read(5)


def test_read_without_size_does_a_single_recv():
    assert _wrapper([b"abc", b"def"]).read() == b"abc"
