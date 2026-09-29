"""`hash_directory` must ignore files git ignores, so a local scratch file
can't make a workspace package's lock hash differ between machines."""

import subprocess
from pathlib import Path

import pytest

from atlas_composer._hashing import hash_directory


def _git(directory: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=directory, check=True, capture_output=True)


@pytest.fixture
def package(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("local/\n")
    (tmp_path / "module.py").write_text("x = 1\n")
    return tmp_path


def test_git_ignored_files_do_not_change_the_hash(package: Path):
    before = hash_directory(package, algorithm="sha256")

    (package / "local").mkdir()
    (package / "local" / "notes.txt").write_text("scratch")

    assert hash_directory(package, algorithm="sha256") == before


def test_a_new_unstaged_source_file_changes_the_hash(package: Path):
    before = hash_directory(package, algorithm="sha256")

    (package / "other.py").write_text("y = 2\n")

    assert hash_directory(package, algorithm="sha256") != before


def test_the_hash_is_the_same_whether_or_not_files_are_staged(package: Path):
    unstaged = hash_directory(package, algorithm="sha256")

    _git(package, "add", ".")

    assert hash_directory(package, algorithm="sha256") == unstaged


def test_outside_a_git_checkout_every_file_is_hashed(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    (tmp_path / "module.py").write_text("x = 1\n")
    before = hash_directory(tmp_path, algorithm="sha256")

    (tmp_path / "extra.txt").write_text("z")

    assert hash_directory(tmp_path, algorithm="sha256") != before
