# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.tools.fs.file_access_policy import FileAccessError, FileAccessPolicy, canonicalize_path

# ---------------------------------------------------------------------------
# canonicalize_path
# ---------------------------------------------------------------------------


def test_canonicalize_path_expands_tilde(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows uses USERPROFILE, not HOME
    assert canonicalize_path("~/foo") == tmp_path / "foo"


def test_canonicalize_path_is_idempotent(tmp_path) -> None:
    p = tmp_path / "sub" / "file.txt"
    assert canonicalize_path(str(p)) == canonicalize_path(canonicalize_path(str(p)))


def test_canonicalize_path_accepts_path_object(tmp_path) -> None:
    assert canonicalize_path(tmp_path / "x.txt") == tmp_path / "x.txt"


# ---------------------------------------------------------------------------
# assert_* return canonical path
# ---------------------------------------------------------------------------


def test_assert_readable_returns_canonical_path(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    returned = policy.assert_readable(str(tmp_path / "file.txt"))
    assert returned == tmp_path / "file.txt"


def test_assert_writable_returns_canonical_path(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    returned = policy.assert_writable(str(tmp_path / "file.txt"))
    assert returned == tmp_path / "file.txt"


def test_assert_readable_expands_tilde(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows uses USERPROFILE, not HOME
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    returned = policy.assert_readable("~/file.txt")
    assert returned == tmp_path / "file.txt"


# ---------------------------------------------------------------------------
# write_root enforcement
# ---------------------------------------------------------------------------


def test_write_inside_root_allowed(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    policy.assert_writable(str(tmp_path / "sub" / "file.txt"))


def test_write_outside_root_denied(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    with pytest.raises(FileAccessError, match="outside write root"):
        policy.assert_writable(str(tmp_path.parent / "outside.txt"))


def test_write_traversal_denied(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    with pytest.raises(FileAccessError, match="outside write root"):
        policy.assert_writable(str(tmp_path / ".." / "escape.txt"))


def test_write_symlink_escaping_root_denied(tmp_path) -> None:
    outside = tmp_path.parent / "outside_target"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link_to_outside"
    link.symlink_to(outside)

    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=())
    with pytest.raises(FileAccessError, match="outside write root"):
        policy.assert_writable(str(link / "file.txt"))


# ---------------------------------------------------------------------------
# Inside write_root: deny patterns are bypassed for both reads and writes
# ---------------------------------------------------------------------------


def test_read_denied_basename_inside_write_root_is_allowed(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(".env",))
    policy.assert_readable(str(tmp_path / ".env"))


def test_read_denied_path_pattern_inside_write_root_is_allowed(tmp_path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(f"{secrets}/*",))
    policy.assert_readable(str(secrets / "key.txt"))


def test_write_denied_basename_inside_write_root_is_allowed(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(".env",))
    policy.assert_writable(str(tmp_path / ".env"))


def test_write_denied_path_pattern_inside_write_root_is_allowed(tmp_path) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=(f"{secrets}/*",))
    policy.assert_writable(str(secrets / "x.txt"))


# ---------------------------------------------------------------------------
# Outside write_root: deny patterns still apply to reads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [".env", ".env.local", ".envrc", ".netrc", "secret.pem", "private.key"],
)
def test_basename_pattern_denies_read_outside_write_root(tmp_path, filename) -> None:
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root)  # default patterns
    with pytest.raises(FileAccessError, match="Read denied"):
        policy.assert_readable(str(tmp_path / filename))


@pytest.mark.parametrize("filename", ["app.py", "README.md", "config.yaml", "env.txt"])
def test_basename_pattern_allows_unrelated_outside_write_root(tmp_path, filename) -> None:
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root)
    policy.assert_readable(str(tmp_path / filename))


def test_custom_basename_pattern_denies_outside_write_root(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=("*.secret",))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(tmp_path / "api.secret"))
    policy.assert_readable(str(tmp_path / "api.public"))


# ---------------------------------------------------------------------------
# Path pattern semantics — match against full canonical path string
# ---------------------------------------------------------------------------


def test_path_pattern_denies_outside_write_root(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    denied = tmp_path / "secrets"
    denied.mkdir()
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{denied}/*",))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(denied / "x.txt"))
    # fnmatch's '*' is greedy across '/', so subpaths are also denied
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(denied / "sub" / "deep.txt"))


def test_path_pattern_allows_siblings_outside_write_root(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    denied = tmp_path / "secrets"
    denied.mkdir()
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{denied}/*",))
    policy.assert_readable(str(tmp_path / "public.txt"))


def test_specific_path_pattern_denies_only_that_file(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    (tmp_path / "secrets").mkdir()
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{tmp_path}/secrets/credentials",))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(tmp_path / "secrets" / "credentials"))
    # same name elsewhere is fine
    policy.assert_readable(str(tmp_path / "credentials"))


def test_path_pattern_with_glob_in_middle(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    base = tmp_path / "dir"
    base.mkdir()
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{base}/*credentials*",))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(base / "my_credentials_file"))
    # '*' spans '/', so a deeper file with 'credentials' in the name is still denied
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(base / "sub" / "credentials.txt"))


def test_path_pattern_resolves_symlinked_root(tmp_path) -> None:
    """Pattern's static prefix is resolved at __init__ so symlinks can't bypass."""
    write_root = tmp_path / "sandbox"
    real = tmp_path / "real_secrets"
    real.mkdir()
    (real / "key").write_text("x")
    link = tmp_path / "link_secrets"
    link.symlink_to(real)

    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{link}/*",))
    # accessing via the real path is denied
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(real / "key"))
    # accessing via the symlinked path is also denied (same resolved target)
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(link / "key"))


def test_symlink_to_denied_target_is_blocked(tmp_path) -> None:
    """A symlink in an allowed dir pointing into a denied tree is still denied."""
    write_root = tmp_path / "sandbox"
    denied = tmp_path / "secrets"
    denied.mkdir()
    target = denied / "key"
    target.write_text("x")
    public = tmp_path / "innocent_link"
    public.symlink_to(target)

    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{denied}/*",))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(public))


def test_traversal_does_not_bypass(tmp_path) -> None:
    write_root = tmp_path / "sandbox"
    denied = tmp_path / "secrets"
    denied.mkdir()
    (denied / "key").write_text("x")
    policy = FileAccessPolicy(write_root=write_root, deny_patterns=(f"{denied}/*",))
    with pytest.raises(FileAccessError):
        policy.assert_readable(str(tmp_path / "public" / ".." / "secrets" / "key"))


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


def test_deny_patterns_property_preserves_input(tmp_path) -> None:
    patterns = ("*.pem", "~/.ssh/*", ".env")
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=patterns)
    assert policy.deny_patterns == patterns


def test_basename_patterns_filters_to_basename_only(tmp_path) -> None:
    policy = FileAccessPolicy(write_root=tmp_path, deny_patterns=("*.pem", "~/.ssh/*", ".env"))
    assert set(policy.basename_patterns) == {"*.pem", ".env"}


# ---------------------------------------------------------------------------
# DEFAULT_DENY_PATTERNS — coverage for the rooted secret directories
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("root", ["~/.aws", "~/.kube", "~/.gnupg", "~/.docker", "~/.config/gcloud", "~/.ssh"])
def test_read_denied_by_default_path_pattern(tmp_path, root) -> None:
    write_root = tmp_path / "sandbox"
    policy = FileAccessPolicy(write_root=write_root)
    resolved_root = canonicalize_path(root)
    with pytest.raises(FileAccessError, match="Read denied"):
        policy.assert_readable(str(resolved_root / "config"))
