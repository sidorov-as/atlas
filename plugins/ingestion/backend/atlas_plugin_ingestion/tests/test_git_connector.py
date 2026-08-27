"""Unit tests for `connectors.git.GitConnector` (one universal `GitConnector`
via shallow clone; `dulwich` + `paramiko`, not subprocess `git`/`ssh`; SSH
host-key verification is fail-closed by default).

No real network here — `_build_client` is monkeypatched with a fake
`GitClient` stub that writes fixture files into the target directory, the
same shape a real `dulwich` clone leaves behind. Real-transport coverage
(actual HTTPS/SSH clones, fail-closed host-key rejection against a live
mismatch) lives in `test_git_connector_integration.py`.
"""

import io
import subprocess
import time
from pathlib import Path

import paramiko
import pytest

from atlas_plugin_ingestion.connectors import git as git_module
from atlas_plugin_ingestion.connectors.git import (
    CloneTimeoutError,
    GitConnector,
    GitConnectorConfigError,
    SourceConnection,
    UnsupportedPrivateKeyError,
    _build_client,
    _FailClosedSSHVendor,
    _load_private_key,
    _validate_scheme,
)
from atlas_plugin_ingestion.models import RegisteredRepository


def _repo(**overrides) -> RegisteredRepository:
    fields = {
        "source_id": "test-source",
        "path": "org/repo",
        "default_branch": "main",
        **overrides,
    }
    return RegisteredRepository(**fields)


def _rsa_private_key_pem() -> str:
    key = paramiko.RSAKey.generate(2048)
    buf = io.StringIO()
    key.write_private_key(buf)
    return buf.getvalue()


class _FakeDulwichRepo:
    def __init__(self, head_sha: bytes) -> None:
        self._head_sha = head_sha
        self.closed = False

    def head(self) -> bytes:
        return self._head_sha

    def close(self) -> None:
        self.closed = True


class _FakeGitClient:
    """Stands in for a real `dulwich.client.GitClient`: `.clone()` writes
    `files` into `target_path` and returns a fake repo, without touching
    the network."""

    def __init__(
        self,
        files: dict[str, bytes],
        *,
        head_sha: bytes = b"a" * 40,
        delay: float = 0.0,
        fail: bool = False,
    ) -> None:
        self.files = files
        self.head_sha = head_sha
        self.delay = delay
        self.fail = fail
        self.clone_calls = 0
        self.last_repo: _FakeDulwichRepo | None = None

    def clone(self, path, target_path, *, mkdir, checkout, branch, depth):
        self.clone_calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            msg = "simulated clone failure"
            raise RuntimeError(msg)
        for rel_path, content in self.files.items():
            full = Path(target_path) / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(content)
        self.last_repo = _FakeDulwichRepo(self.head_sha)
        return self.last_repo


def _patch_build_client(monkeypatch, fake_client: _FakeGitClient) -> None:
    monkeypatch.setattr(
        git_module,
        "_build_client",
        lambda connection, scheme: (fake_client, ""),
    )


# -- transport scheme allowlist -----------------------------------


def test_validate_scheme_accepts_https_http_ssh():
    assert _validate_scheme("https://example.com") == "https"
    assert _validate_scheme("http://example.com") == "http"
    assert _validate_scheme("ssh://git@example.com") == "ssh"


@pytest.mark.parametrize(
    "base_url",
    ["git://example.com", "file:///tmp/repo", "ext::sh -c evil"],
)
def test_validate_scheme_rejects_other_schemes(base_url):
    with pytest.raises(GitConnectorConfigError, match="unsupported"):
        _validate_scheme(base_url)


def test_connector_construction_rejects_disallowed_scheme():
    connection = SourceConnection(
        base_url="git://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    with pytest.raises(GitConnectorConfigError):
        GitConnector(connection)


# -- SSH host-key verification is fail-closed by default ---------


def test_ssh_vendor_requires_known_hosts_or_accept_unknown_host_keys():
    connection = SourceConnection(
        base_url="ssh://git@example.com",
        auth_kind="ssh-key",
        credential=_rsa_private_key_pem(),
    )
    with pytest.raises(GitConnectorConfigError, match="known_hosts"):
        _FailClosedSSHVendor(connection)


def test_ssh_vendor_accepts_known_hosts_only():
    connection = SourceConnection(
        base_url="ssh://git@example.com",
        auth_kind="ssh-key",
        credential=_rsa_private_key_pem(),
        known_hosts="example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA==",
    )
    _FailClosedSSHVendor(connection)


def test_ssh_vendor_accepts_accept_unknown_host_keys_only():
    connection = SourceConnection(
        base_url="ssh://git@example.com",
        auth_kind="ssh-key",
        credential=_rsa_private_key_pem(),
        accept_unknown_host_keys=True,
    )
    _FailClosedSSHVendor(connection)


# -- private key parsing -----------------------------------------------------


def test_load_private_key_parses_a_recognized_key_format():
    key = _load_private_key(_rsa_private_key_pem())
    assert key.get_name() == "ssh-rsa"


def test_load_private_key_raises_on_unrecognized_content():
    with pytest.raises(UnsupportedPrivateKeyError):
        _load_private_key("not a private key")


# -- HTTPS auth: headers, never the clone URL ---------------------


def test_build_client_basic_auth_sets_authorization_header():
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="alice:s3cret",
    )
    client, _ = _build_client(connection, "https")

    assert client._auth_header is not None
    import base64

    scheme, _, encoded = client._auth_header.partition(" ")
    assert scheme.lower() == "basic"
    assert base64.b64decode(encoded).decode() == "alice:s3cret"


def test_build_client_bearer_auth_attaches_authorization_header():
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="bearer",
        credential="tok-abc123",
    )
    client, _ = _build_client(connection, "https")

    assert client.pool_manager.headers["Authorization"] == "Bearer tok-abc123"


def test_build_client_rejects_unsupported_auth_kind_over_https():
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="ssh-key",
        credential="x",
    )
    with pytest.raises(GitConnectorConfigError):
        _build_client(connection, "https")


def test_build_client_rejects_unsupported_auth_kind_over_ssh():
    connection = SourceConnection(
        base_url="ssh://git@example.com",
        auth_kind="basic",
        credential="u:p",
    )
    with pytest.raises(GitConnectorConfigError):
        _build_client(connection, "ssh")


# -- clone lifecycle: caching, cleanup, timeout ------------------------------------


def test_checkout_is_cloned_once_and_reused_across_calls(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"kind: Component\n"})
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)
    repo = _repo()

    sha = connector.get_head_sha(repo)
    paths = connector.list_manifest_paths(repo)
    content = connector.fetch_file(repo, "catalog-info.yaml", sha)

    assert fake_client.clone_calls == 1
    assert sha == "a" * 40
    assert paths == ["catalog-info.yaml"]
    assert content == b"kind: Component\n"
    connector.close()


def test_manifest_paths_discovers_nested_files_and_skips_git_dir(monkeypatch):
    fake_client = _FakeGitClient(
        {
            "catalog-info.yaml": b"root",
            "nested/catalog-info.yaml": b"nested",
            ".git/catalog-info.yaml": b"must not be discovered",
        },
    )
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)

    paths = connector.list_manifest_paths(_repo())

    assert paths == ["catalog-info.yaml", "nested/catalog-info.yaml"]
    connector.close()


def test_close_removes_the_cloned_temporary_directory(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"})
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)
    connector.list_manifest_paths(_repo())
    directory = Path(next(iter(connector._checkouts.values())).directory)
    assert directory.exists()

    connector.close()

    assert not directory.exists()
    assert fake_client.last_repo.closed is True


def test_context_manager_closes_on_exit(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"})
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    with GitConnector(connection) as connector:
        connector.list_manifest_paths(_repo())
        directory = Path(next(iter(connector._checkouts.values())).directory)

    assert not directory.exists()


def test_clone_timeout_raises_and_cleans_up_the_temp_directory(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"}, delay=0.3)
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
        timeout=0.05,
    )
    connector = GitConnector(connection)

    with pytest.raises(CloneTimeoutError):
        connector.get_head_sha(_repo())

    assert connector._checkouts == {}


def test_cleanup_on_clone_failure_removes_the_temp_directory(monkeypatch):
    fake_client = _FakeGitClient({}, fail=True)
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)

    created_dirs: list[str] = []
    original_mkdtemp = git_module.tempfile.mkdtemp

    def _tracking_mkdtemp(*args, **kwargs):
        directory = original_mkdtemp(*args, **kwargs)
        created_dirs.append(directory)
        return directory

    monkeypatch.setattr(git_module.tempfile, "mkdtemp", _tracking_mkdtemp)

    with pytest.raises(RuntimeError, match="simulated clone failure"):
        connector.get_head_sha(_repo())

    assert created_dirs
    assert not Path(created_dirs[0]).exists()


def test_no_subprocess_is_invoked_during_a_clone(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"})
    _patch_build_client(monkeypatch, fake_client)

    def _forbidden(*args, **kwargs):
        msg = "subprocess must never be invoked by the git connector"
        raise AssertionError(msg)

    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    monkeypatch.setattr(subprocess, "run", _forbidden)

    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)
    connector.get_head_sha(_repo())
    connector.close()


# -- containment re-verified at the read boundary, independent of whatever
# pre-check the caller ran ----------------------------------------------------


def test_fetch_file_rejects_an_absolute_path(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"})
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)
    repo = _repo()
    sha = connector.get_head_sha(repo)

    with pytest.raises(ValueError, match="not contained"):
        connector.fetch_file(repo, "/etc/passwd", sha)

    connector.close()


def test_fetch_file_rejects_dot_dot_traversal(monkeypatch):
    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"})
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)
    repo = _repo()
    sha = connector.get_head_sha(repo)

    with pytest.raises(ValueError, match="not contained"):
        connector.fetch_file(repo, "../../etc/passwd", sha)

    connector.close()


def test_fetch_file_rejects_a_symlink_escaping_the_checkout(monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("top secret")

    fake_client = _FakeGitClient({"catalog-info.yaml": b"x"})
    _patch_build_client(monkeypatch, fake_client)
    connection = SourceConnection(
        base_url="https://example.com",
        auth_kind="basic",
        credential="u:p",
    )
    connector = GitConnector(connection)
    repo = _repo()
    sha = connector.get_head_sha(repo)
    checkout_dir = Path(next(iter(connector._checkouts.values())).directory)
    (checkout_dir / "escape").symlink_to(outside / "secret.txt")

    with pytest.raises(ValueError, match="not contained"):
        connector.fetch_file(repo, "escape", sha)

    connector.close()
