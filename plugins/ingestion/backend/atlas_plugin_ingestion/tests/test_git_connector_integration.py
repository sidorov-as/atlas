"""Integration tests for `connectors.git.GitConnector` against a real,
throwaway local Gitea instance (successful HTTPS clone and SSH
clone against a throwaway local git server, and a test asserting no
`subprocess` call occurs during either transport).

Skipped entirely when Docker isn't reachable — these are the only tests in
the ingestion plugin's suite that need it; everything else in
`test_git_connector.py` runs against a mocked transport and needs no
external service.
"""

import base64
import io
import shutil
import subprocess
import time
import uuid
from collections.abc import Iterator

import paramiko
import pytest
import requests

from atlas_plugin_ingestion.connectors.git import GitConnector, SourceConnection
from atlas_plugin_ingestion.models import RegisteredRepository

HTTP_PORT = 23000
SSH_PORT = 23022
GITEA_IMAGE = "gitea/gitea:1.22"
ADMIN_USER = "spike"
ADMIN_PASSWORD = "spikepass123"
REPO_NAME = "connector-repo"


def _docker_available() -> bool:
    probe = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    return shutil.which("docker") is not None and probe.returncode == 0


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="docker is not available",
)


class _GiteaServer:
    def __init__(
        self,
        base_url: str,
        ssh_url: str,
        private_key: str,
        known_hosts: str,
    ) -> None:
        self.base_url = base_url
        self.ssh_url = ssh_url
        self.private_key = private_key
        self.known_hosts = known_hosts


def _wait_for_http(url: str, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if requests.get(url, timeout=2).status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    msg = f"{url} did not become ready within {timeout}s"
    raise TimeoutError(msg)


def _docker_rm(container_name: str) -> None:
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        check=False,
    )


@pytest.fixture(scope="module")
def gitea() -> Iterator[_GiteaServer]:
    container_name = f"atlas-ingestion-test-gitea-{uuid.uuid4().hex[:8]}"
    _docker_rm(container_name)
    root_url = f"GITEA__server__ROOT_URL=http://localhost:{HTTP_PORT}/"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-e",
            "GITEA__security__INSTALL_LOCK=true",
            "-e",
            "GITEA__database__DB_TYPE=sqlite3",
            "-e",
            "GITEA__server__DOMAIN=localhost",
            "-e",
            root_url,
            "-e",
            "GITEA__service__DISABLE_REGISTRATION=true",
            "-p",
            f"{HTTP_PORT}:3000",
            "-p",
            f"{SSH_PORT}:22",
            GITEA_IMAGE,
        ],
        check=True,
        capture_output=True,
    )
    try:
        base_url = f"http://localhost:{HTTP_PORT}"
        _wait_for_http(f"{base_url}/api/v1/version")

        subprocess.run(
            [
                "docker",
                "exec",
                "-u",
                "git",
                container_name,
                "gitea",
                "admin",
                "user",
                "create",
                "--username",
                ADMIN_USER,
                "--password",
                ADMIN_PASSWORD,
                "--email",
                "spike@example.com",
                "--admin",
                "--must-change-password=false",
            ],
            check=True,
            capture_output=True,
        )

        auth = (ADMIN_USER, ADMIN_PASSWORD)
        response = requests.post(
            f"{base_url}/api/v1/user/repos",
            auth=auth,
            json={
                "name": REPO_NAME,
                "auto_init": True,
                "default_branch": "main",
            },
            timeout=10,
        )
        response.raise_for_status()

        manifests = (
            (
                "catalog-info.yaml",
                b"kind: Component\nmetadata:\n  name: root\n",
            ),
            (
                "nested/catalog-info.yaml",
                b"kind: Component\nmetadata:\n  name: nested\n",
            ),
        )
        for rel_path, content in manifests:
            contents_url = (
                f"{base_url}/api/v1/repos/{ADMIN_USER}/{REPO_NAME}"
                f"/contents/{rel_path.replace('/', '%2F')}"
            )
            requests.post(
                contents_url,
                auth=auth,
                json={
                    "content": base64.b64encode(content).decode(),
                    "message": f"add {rel_path}",
                    "branch": "main",
                },
                timeout=10,
            ).raise_for_status()

        # Gitea's default policy rejects RSA keys shorter than 3072 bits.
        key = paramiko.RSAKey.generate(4096)
        private_key_buf = io.StringIO()
        key.write_private_key(private_key_buf)
        public_key = f"{key.get_name()} {key.get_base64()}"

        requests.post(
            f"{base_url}/api/v1/user/keys",
            auth=auth,
            json={"title": "integration-test-key", "key": public_key},
            timeout=10,
        ).raise_for_status()

        keyscan = subprocess.run(
            ["ssh-keyscan", "-p", str(SSH_PORT), "-t", "ed25519", "localhost"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        known_hosts = "\n".join(
            line for line in keyscan.stdout.splitlines() if not line.startswith("#")
        )

        yield _GiteaServer(
            base_url=base_url,
            ssh_url=f"ssh://git@localhost:{SSH_PORT}",
            private_key=private_key_buf.getvalue(),
            known_hosts=known_hosts,
        )
    finally:
        _docker_rm(container_name)


@pytest.fixture
def repo() -> RegisteredRepository:
    return RegisteredRepository(
        source_id="gitea",
        path=f"{ADMIN_USER}/{REPO_NAME}",
        default_branch="main",
    )


def _assert_full_round_trip(
    connector: GitConnector,
    repo: RegisteredRepository,
) -> None:
    sha = connector.get_head_sha(repo)
    assert len(sha) == 40

    paths = connector.list_manifest_paths(repo)
    assert paths == ["catalog-info.yaml", "nested/catalog-info.yaml"]

    root_content = connector.fetch_file(repo, "catalog-info.yaml", sha)
    assert b"name: root" in root_content
    nested_content = connector.fetch_file(
        repo,
        "nested/catalog-info.yaml",
        sha,
    )
    assert b"name: nested" in nested_content


def test_https_basic_auth_clone_round_trip(gitea, repo):
    connection = SourceConnection(
        base_url=gitea.base_url,
        auth_kind="basic",
        credential=f"{ADMIN_USER}:{ADMIN_PASSWORD}",
    )
    with GitConnector(connection) as connector:
        _assert_full_round_trip(connector, repo)


def test_https_bearer_auth_clone_round_trip(gitea, repo):
    token_response = requests.post(
        f"{gitea.base_url}/api/v1/users/{ADMIN_USER}/tokens",
        auth=(ADMIN_USER, ADMIN_PASSWORD),
        json={
            "name": f"it-{uuid.uuid4().hex[:8]}",
            "scopes": ["write:repository"],
        },
        timeout=10,
    )
    token_response.raise_for_status()
    token = token_response.json()["sha1"]

    connection = SourceConnection(
        base_url=gitea.base_url,
        auth_kind="bearer",
        credential=token,
    )
    # The connector always sends `Authorization: Bearer <credential>` for
    # `auth_kind: bearer`; Gitea's git-smart-http accepts that scheme for a
    # personal access token same as it accepts Basic auth.
    with GitConnector(connection) as connector:
        sha = connector.get_head_sha(repo)
        assert len(sha) == 40


def test_ssh_key_auth_clone_round_trip(gitea, repo):
    connection = SourceConnection(
        base_url=gitea.ssh_url,
        auth_kind="ssh-key",
        credential=gitea.private_key,
        known_hosts=gitea.known_hosts,
    )
    with GitConnector(connection) as connector:
        _assert_full_round_trip(connector, repo)


def test_ssh_fails_closed_on_a_mismatched_host_key(gitea, repo):
    real_key_data = gitea.known_hosts.split()[-1]
    corrupted = real_key_data[:-4] + (
        "zzzz" if real_key_data[-4:] != "zzzz" else "aaaa"
    )
    bad_known_hosts = gitea.known_hosts.replace(real_key_data, corrupted)
    connection = SourceConnection(
        base_url=gitea.ssh_url,
        auth_kind="ssh-key",
        credential=gitea.private_key,
        known_hosts=bad_known_hosts,
    )
    with (
        GitConnector(connection) as connector,
        pytest.raises(Exception, match="(?i)host key|does not match"),
    ):
        connector.get_head_sha(repo)


def test_no_subprocess_is_invoked_for_a_real_https_clone(
    gitea,
    repo,
    monkeypatch,
):
    def _forbidden(*args, **kwargs):
        msg = f"unexpected subprocess.Popen call: {args!r}"
        raise AssertionError(msg)

    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    connection = SourceConnection(
        base_url=gitea.base_url,
        auth_kind="basic",
        credential=f"{ADMIN_USER}:{ADMIN_PASSWORD}",
    )
    with GitConnector(connection) as connector:
        connector.get_head_sha(repo)


def test_no_subprocess_is_invoked_for_a_real_ssh_clone(
    gitea,
    repo,
    monkeypatch,
):
    def _forbidden(*args, **kwargs):
        msg = f"unexpected subprocess.Popen call: {args!r}"
        raise AssertionError(msg)

    monkeypatch.setattr(subprocess, "Popen", _forbidden)
    connection = SourceConnection(
        base_url=gitea.ssh_url,
        auth_kind="ssh-key",
        credential=gitea.private_key,
        known_hosts=gitea.known_hosts,
    )
    with GitConnector(connection) as connector:
        connector.get_head_sha(repo)
