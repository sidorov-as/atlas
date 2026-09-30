"""Provider-agnostic `SourceConnector` implementation (one universal
`GitConnector` via shallow clone): discovers and reads
`catalog-info.yaml` via a shallow (`depth=1`, single-branch) `dulwich` clone
over HTTPS or SSH, with SSH backed by `paramiko` — never a subprocess `git`
or `ssh` invocation (`dulwich` + `paramiko`, not subprocess
`git`/`ssh`), which closes the `ext::`-transport and SSH-argument-injection
command-injection classes by construction.

`GitConnector` is constructed with a `SourceConnection` — deployment-level
connection details for one `atlas.ingestion` `sources[]` entry, already
resolved via `resolve_secrets` (no `SecretRef`/`FileRef` reaches this
module). `plugin.py`'s `register_runtime` builds one `SourceConnection` per
configured source from the plugin's resolved `IngestionPluginConfig` and
registers a fresh-connector factory per source id against the
`atlas.ingestion.connectors.v1` extension point; `pipeline.py` resolves the
factory for a given repository's `source_id` and constructs a connector for
that one repository's clone (see "Clone lifecycle" below) — this module
only implements the connector itself and is covered by its own
unit/integration tests.

`SourceConnection.credential` is a single opaque string whose shape depends
on `auth_kind`:
  - `basic`: `"<username>:<password>"` (never embedded in the clone URL —
    sent as a `Basic` `Authorization` header, mirroring RFC 7617).
  - `bearer`: the raw token, sent as `Authorization: Bearer <token>`.
  - `ssh-key`: PEM-encoded private key content (a `FileRef`-resolved value
    upstream).

Clone lifecycle: one clone per repository per
pass, cached for the life of this `GitConnector` instance so `get_head_sha`,
`list_manifest_paths`, and `fetch_file` share one local checkout instead of
a network round trip each — call `close()` (or use this connector as a
context manager) once a pass is done with it, which removes every cloned
temporary directory regardless of how the pass ended.
"""

import io
import os
import shutil
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Self
from urllib.parse import urlsplit

import paramiko
import urllib3
from dulwich.client import GitClient, HttpGitClient, SSHGitClient, SSHVendor
from dulwich.repo import Repo as DulwichRepo

from atlas_plugin_ingestion.models import RegisteredRepository

from ..paths import resolve_repository_relative
from .base import MANIFEST_FILENAME, SourceConnector

ALLOWED_SCHEMES = frozenset({"https", "http", "ssh"})
DEFAULT_CLONE_TIMEOUT_SECONDS = 60.0

_SSH_KEY_CLASSES = (
    paramiko.Ed25519Key,
    paramiko.RSAKey,
    paramiko.ECDSAKey,
)


class GitConnectorConfigError(Exception):
    """Raised when a `SourceConnection` can't produce a working clone: an
    unsupported transport scheme, or an `ssh-key` source with neither
    known-hosts data nor the explicit development opt-in configured."""


class CloneTimeoutError(Exception):
    """Raised when a clone operation exceeds `SourceConnection.timeout`
    (a wall-clock timeout per clone operation)."""


class UnsupportedPrivateKeyError(Exception):
    """Raised when `SourceConnection.credential` for an `ssh-key` source
    isn't a private key format paramiko recognizes."""


@dataclass(frozen=True)
class SourceConnection:
    """Resolved, deployment-level connection details for one configured
    `atlas.ingestion` source (deployment-level `sources` in
    plugin config") — everything `GitConnector` needs to reach one git
    host. `credential` is always the already-resolved literal secret value;
    no `SecretRef`/`FileRef` reaches this class."""

    base_url: str
    auth_kind: str
    credential: str
    known_hosts: str | None = None
    accept_unknown_host_keys: bool = False
    timeout: float = DEFAULT_CLONE_TIMEOUT_SECONDS


class _ParamikoChannelWrapper:
    """Adapts a paramiko `Channel` to the small `can_read`/`write`/`read`/
    `close` protocol `dulwich.client.SSHVendor.run_command` is expected to
    return."""

    def __init__(
        self,
        client: paramiko.SSHClient,
        channel: paramiko.Channel,
    ) -> None:
        self._client = client
        self._channel = channel

    def can_read(self) -> bool:
        return self._channel.recv_ready()

    def write(self, data: bytes) -> None:
        self._channel.sendall(data)

    def read(self, n: int | None = None) -> bytes:
        # dulwich treats this like a file object: `read(n)` must return
        # exactly `n` bytes unless the stream ended. `Channel.recv` returns
        # whatever has arrived (often less), which surfaces as a flaky
        # "Length of pkt read ... does not match length prefix" error.
        if n is None:
            data = self._channel.recv(65536)
            if not data:
                raise ConnectionError("git-over-ssh connection closed unexpectedly")
            return data
        chunks: list[bytes] = []
        remaining = n
        while remaining > 0:
            data = self._channel.recv(remaining)
            if not data:
                break
            chunks.append(data)
            remaining -= len(data)
        if not chunks:
            raise ConnectionError("git-over-ssh connection closed unexpectedly")
        return b"".join(chunks)

    def close(self) -> None:
        self._channel.close()
        self._client.close()


def _load_private_key(credential: str) -> paramiko.PKey:
    """Auto-detect and parse `credential` (PEM key content) against every
    key type paramiko supports — there is no cross-type "just load it"
    helper on `PKey` itself, only per-type `from_private_key`."""
    for key_cls in _SSH_KEY_CLASSES:
        try:
            return key_cls.from_private_key(io.StringIO(credential))
        except (paramiko.SSHException, ValueError):
            continue
    raise UnsupportedPrivateKeyError(
        "credential is not a private key format paramiko recognizes "
        "(tried ed25519, rsa, ecdsa)",
    )


class _FailClosedSSHVendor(SSHVendor):
    """`SSHVendor` backed directly by `paramiko.SSHClient` — never shells
    out to the system `ssh` binary (`dulwich` + `paramiko`, not
    subprocess `git`/`ssh`). Host-key verification is fail-closed by
    default): a host key not present in `known_hosts` is rejected unless
    `accept_unknown_host_keys` is explicitly set. paramiko itself still
    rejects a host key that mismatches a *known* entry regardless of that
    flag — it only governs what happens for a host with no entry at all."""

    def __init__(self, connection: SourceConnection) -> None:
        if not connection.known_hosts and not connection.accept_unknown_host_keys:
            raise GitConnectorConfigError(
                "ssh-key source has neither known_hosts nor "
                "accept_unknown_host_keys configured; refusing to connect "
                "without a way to verify the remote host key",
            )
        self._connection = connection
        self._host_keys = _parse_known_hosts(connection.known_hosts or "")

    def run_command(
        self,
        host: str,
        command: bytes,
        username: str | None = None,
        port: int | None = None,
        password: str | None = None,
        pkey: paramiko.PKey | None = None,
        key_filename: str | None = None,
        ssh_command: str | None = None,
        protocol_version: int | None = None,
        **kwargs: object,
    ) -> _ParamikoChannelWrapper:
        client = paramiko.SSHClient()
        for hostname, keys in self._host_keys.items():
            for keytype, key in keys.items():
                client.get_host_keys().add(hostname, keytype, key)
        client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
            if self._connection.accept_unknown_host_keys
            else paramiko.RejectPolicy()
        )
        if pkey is None:
            pkey = _load_private_key(self._connection.credential)
        client.connect(
            hostname=host,
            port=port or 22,
            username=username,
            pkey=pkey,
            allow_agent=False,
            look_for_keys=False,
            timeout=self._connection.timeout,
        )
        transport = client.get_transport()
        if transport is None:
            msg = f"failed to establish an SSH transport to {host}"
            raise ConnectionError(msg)
        channel = transport.open_session()
        if protocol_version is None or protocol_version == 2:
            channel.set_environment_variable(
                name="GIT_PROTOCOL",
                value="version=2",
            )
        channel.exec_command(command.decode())
        return _ParamikoChannelWrapper(client, channel)


def _parse_known_hosts(known_hosts: str) -> paramiko.HostKeys:
    host_keys = paramiko.HostKeys()
    for line in known_hosts.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        entry = paramiko.hostkeys.HostKeyEntry.from_line(line)
        if entry is None or entry.key is None or entry.hostnames is None:
            continue
        for hostname in entry.hostnames:
            host_keys.add(hostname, entry.key.get_name(), entry.key)
    return host_keys


class _Checkout:
    """One repository's local, shallow, single-branch clone — the shared
    state `get_head_sha`/`list_manifest_paths`/`fetch_file` read from
    within a single ingestion pass."""

    def __init__(self, directory: str, repo: DulwichRepo) -> None:
        self.directory = directory
        self._repo = repo

    @property
    def head_sha(self) -> str:
        return self._repo.head().decode("ascii")

    def manifest_paths(self) -> list[str]:
        root = Path(self.directory)
        found: list[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            if MANIFEST_FILENAME in filenames:
                rel = Path(dirpath).relative_to(root) / MANIFEST_FILENAME
                found.append(rel.as_posix())
        return sorted(found)

    def all_paths(self) -> list[str]:
        root = Path(self.directory)
        found: list[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for filename in filenames:
                rel = Path(dirpath).relative_to(root) / filename
                found.append(rel.as_posix())
        return sorted(found)

    def read(self, path: str) -> bytes:
        """`path`'s bytes, re-verifying containment within this checkout
        independently of whatever pre-check the caller already ran
        (containment is enforced inside the connector's read path,
        not only at the callers) — so a future caller of `fetch_file` that
        forgets to pre-validate still can't escape the checkout, and a
        symlink that stays syntactically in-bounds but escapes on disk is
        still caught here."""
        checkout_root = Path(self.directory)
        resolved = resolve_repository_relative(PurePosixPath("."), path, checkout_root)
        if resolved is None:
            msg = f"path {path!r} is not contained within the repository checkout"
            raise ValueError(msg)
        return resolved.read_bytes()

    def close(self) -> None:
        self._repo.close()
        shutil.rmtree(self.directory, ignore_errors=True)


def _validate_scheme(base_url: str) -> str:
    scheme = urlsplit(base_url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise GitConnectorConfigError(
            f"unsupported source base_url scheme {scheme!r}; only "
            f"{sorted(ALLOWED_SCHEMES)} are allowed",
        )
    return scheme


def _build_client(
    connection: SourceConnection,
    scheme: str,
) -> tuple[GitClient, str]:
    """A `(client, host_relative_path_prefix)` pair for `connection`'s
    transport. `path_prefix` is the part of `base_url` after the host, to
    prepend to a repository's own relative path."""
    split = urlsplit(connection.base_url)
    if scheme in ("https", "http"):
        if connection.auth_kind == "basic":
            username, _, password = connection.credential.partition(":")
            client: GitClient = HttpGitClient(
                connection.base_url,
                username=username,
                password=password,
                timeout=connection.timeout,
            )
        elif connection.auth_kind == "bearer":
            pool_manager = urllib3.PoolManager(
                headers={"Authorization": f"Bearer {connection.credential}"},
            )
            client = HttpGitClient(
                connection.base_url,
                pool_manager=pool_manager,
                timeout=connection.timeout,
            )
        else:
            raise GitConnectorConfigError(
                f"auth_kind {connection.auth_kind!r} is not supported over "
                f"{scheme!r}; use basic or bearer",
            )
        return client, split.path
    if connection.auth_kind != "ssh-key":
        raise GitConnectorConfigError(
            f"auth_kind {connection.auth_kind!r} is not supported over ssh; "
            "use ssh-key",
        )
    vendor = _FailClosedSSHVendor(connection)
    client = SSHGitClient(
        split.hostname,
        port=split.port,
        username=split.username,
        vendor=vendor,
    )
    return client, split.path


def _run_with_timeout(
    func: Callable[[], DulwichRepo],
    timeout: float,
) -> DulwichRepo:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as exc:
            raise CloneTimeoutError(
                f"clone did not complete within {timeout}s",
            ) from exc


class GitConnector(SourceConnector):
    def __init__(self, connection: SourceConnection) -> None:
        self._connection = connection
        self._scheme = _validate_scheme(connection.base_url)
        self._checkouts: dict[int, _Checkout] = {}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        for checkout in self._checkouts.values():
            checkout.close()
        self._checkouts.clear()

    def _repo_relative_path(self, repo: RegisteredRepository) -> str:
        return repo.path

    def _checkout(self, repo: RegisteredRepository) -> _Checkout:
        cached = self._checkouts.get(id(repo))
        if cached is not None:
            return cached

        client, path_prefix = _build_client(self._connection, self._scheme)
        repo_path = self._repo_relative_path(repo).lstrip("/")
        clone_path = f"{path_prefix.rstrip('/')}/{repo_path}"
        directory = tempfile.mkdtemp(prefix="atlas-ingestion-clone-")
        try:
            dulwich_repo = _run_with_timeout(
                lambda: client.clone(
                    clone_path,
                    directory,
                    mkdir=False,
                    checkout=True,
                    branch=repo.default_branch,
                    depth=1,
                ),
                self._connection.timeout,
            )
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise

        checkout = _Checkout(directory, dulwich_repo)
        self._checkouts[id(repo)] = checkout
        return checkout

    def get_head_sha(self, repo: RegisteredRepository) -> str:
        return self._checkout(repo).head_sha

    def list_manifest_paths(self, repo: RegisteredRepository) -> list[str]:
        return self._checkout(repo).manifest_paths()

    def list_paths(self, repo: RegisteredRepository) -> list[str]:
        return self._checkout(repo).all_paths()

    def fetch_file(
        self,
        repo: RegisteredRepository,
        path: str,
        ref: str,
    ) -> bytes:
        return self._checkout(repo).read(path)
