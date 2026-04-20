# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.tools.fs.file_access_policy import FileAccessError, FileAccessPolicy

# ---------------------------------------------------------------------------
# write_root enforcement
# ---------------------------------------------------------------------------


def test_write_inside_root_allowed(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, read_deny_names=(), read_deny_roots=())
    policy.assert_writable(str(tmp_path / "sub" / "file.txt"))


def test_write_outside_root_denied(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, read_deny_names=(), read_deny_roots=())
    with pytest.raises(FileAccessError, match="outside write root"):
        policy.assert_writable(str(tmp_path.parent / "outside.txt"))


def test_write_traversal_denied(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, read_deny_names=(), read_deny_roots=())
    with pytest.raises(FileAccessError, match="outside write root"):
        policy.assert_writable(str(tmp_path / ".." / "escape.txt"))


def test_write_without_root_allowed_anywhere(tmp_path) -> None:
    policy = FileAccessPolicy(read_deny_names=(), read_deny_roots=())
    policy.assert_writable(str(tmp_path / "anywhere.txt"))
    policy.assert_writable("/nonexistent/path.txt")


def test_write_symlink_escaping_root_denied(tmp_path) -> None:
    outside = tmp_path.parent / "outside_target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link_to_outside"
    link.symlink_to(outside)

    policy = FileAccessPolicy(write_root=tmp_path, read_deny_names=(), read_deny_roots=())
    with pytest.raises(FileAccessError, match="outside write root"):
        policy.assert_writable(str(link / "file.txt"))


# ---------------------------------------------------------------------------
# Read denylist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [".env", ".env.local", ".envrc", "secret.pem", "private.key", "id_rsa", "id_rsa.pub"],
)
def test_read_denied_by_default_name(tmp_path, filename) -> None:
    policy = FileAccessPolicy()
    with pytest.raises(FileAccessError, match="Read denied"):
        policy.assert_readable(str(tmp_path / filename))


@pytest.mark.parametrize("filename", ["app.py", "README.md", "config.yaml", "env.txt"])
def test_read_allowed_for_regular_files(tmp_path, filename) -> None:
    policy = FileAccessPolicy(read_deny_roots=())
    policy.assert_readable(str(tmp_path / filename))


def test_custom_deny_name_pattern(tmp_path) -> None:
    policy = FileAccessPolicy(read_deny_names=("*.secret",), read_deny_roots=())
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(tmp_path / "api.secret"))
    policy.assert_readable(str(tmp_path / "api.public"))


def test_deny_root_blocks_nested_paths(tmp_path) -> None:
    denied_root = tmp_path / "private"
    denied_root.mkdir()
    policy = FileAccessPolicy(read_deny_names=(), read_deny_roots=(str(denied_root),))

    with pytest.raises(FileAccessError):
        policy.assert_readable(str(denied_root / "a" / "b.txt"))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(denied_root))


def test_deny_root_does_not_block_siblings(tmp_path) -> None:
    denied_root = tmp_path / "private"
    denied_root.mkdir()
    policy = FileAccessPolicy(read_deny_names=(), read_deny_roots=(str(denied_root),))

    policy.assert_readable(str(tmp_path / "public.txt"))


def test_write_denied_for_denied_names(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, read_deny_roots=())
    with pytest.raises(FileAccessError, match="Write denied"):
        policy.assert_writable(str(tmp_path / ".env"))


def test_write_denied_for_denied_roots(tmp_path) -> None:
    denied = tmp_path / "secrets"
    denied.mkdir()
    policy = FileAccessPolicy(write_root=tmp_path, read_deny_names=(), read_deny_roots=(str(denied),))
    with pytest.raises(FileAccessError, match="Write denied"):
        policy.assert_writable(str(denied / "x.txt"))
