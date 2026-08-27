"""Unit tests for `paths.resolve_repository_relative`: valid relative path, absolute path, `..` traversal,
NUL byte, control character, symlink escaping the checkout.
"""

from pathlib import Path, PurePosixPath

from atlas_plugin_ingestion.paths import resolve_repository_relative


def test_valid_relative_path_resolves_under_the_checkout(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "catalog-info.yaml").write_text("...")

    resolved = resolve_repository_relative(
        PurePosixPath("docs"), "catalog-info.yaml", tmp_path
    )

    assert resolved == (tmp_path / "docs" / "catalog-info.yaml").resolve()


def test_absolute_path_is_rejected(tmp_path: Path) -> None:
    assert (
        resolve_repository_relative(PurePosixPath("docs"), "/etc/passwd", tmp_path)
        is None
    )


def test_dot_dot_traversal_is_rejected(tmp_path: Path) -> None:
    assert (
        resolve_repository_relative(PurePosixPath("docs"), "../../etc/passwd", tmp_path)
        is None
    )


def test_dot_dot_traversal_that_stays_inside_the_checkout_is_still_rejected(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "other.yaml").write_text("...")

    assert (
        resolve_repository_relative(PurePosixPath("docs"), "../other.yaml", tmp_path)
        is None
    )


def test_nul_byte_is_rejected(tmp_path: Path) -> None:
    assert (
        resolve_repository_relative(
            PurePosixPath("docs"), "catalog-info.yaml\x00.txt", tmp_path
        )
        is None
    )


def test_control_character_is_rejected(tmp_path: Path) -> None:
    assert (
        resolve_repository_relative(
            PurePosixPath("docs"), "catalog-info\x1b.yaml", tmp_path
        )
        is None
    )


def test_empty_entry_is_rejected(tmp_path: Path) -> None:
    assert resolve_repository_relative(PurePosixPath("docs"), "", tmp_path) is None


def test_symlink_escaping_the_checkout_is_rejected(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("top secret")
    (checkout / "escape").symlink_to(outside / "secret.txt")

    assert resolve_repository_relative(PurePosixPath("."), "escape", checkout) is None


def test_symlink_staying_inside_the_checkout_is_accepted(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "real.txt").write_text("fine")
    (checkout / "link").symlink_to(checkout / "real.txt")

    resolved = resolve_repository_relative(PurePosixPath("."), "link", checkout)

    assert resolved == (checkout / "real.txt").resolve()
