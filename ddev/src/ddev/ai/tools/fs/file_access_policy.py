# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path

DEFAULT_READ_DENY_NAMES: tuple[str, ...] = (
    ".env",
    ".env.*",
    ".envrc",
    ".netrc",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    "id_ecdsa",
    "id_ecdsa.*",
    "credentials",
    "credentials.json",
)


DEFAULT_READ_DENY_ROOTS: tuple[str, ...] = (
    "~/.ssh",
    "~/.aws",
    "~/.gnupg",
    "~/.config/gcloud",
    "~/.kube",
    "~/.docker",
)


class FileAccessError(Exception):
    """Raised when a file access violates the configured policy."""


class FileAccessPolicy:
    """Global file access policy shared across agents and phases in a run.

    Enforces two rules:
    - Writes must resolve inside write_root (if set).
    - Reads and writes targeting denied paths are refused.

    A path is denied when either condition holds:
    - Its basename matches any pattern in ``read_deny_names`` — this check is
      global and applies regardless of where the file lives.
    - It resolves inside any directory in ``read_deny_roots`` — this check is
      location-based and restricts entire directory trees.

    Paths are resolved before comparison, so symlinks and ``..`` cannot bypass
    the checks.
    """

    def __init__(
        self,
        write_root: Path | None = None,
        read_deny_names: Iterable[str] = DEFAULT_READ_DENY_NAMES,
        read_deny_roots: Iterable[str] = DEFAULT_READ_DENY_ROOTS,
    ) -> None:
        self._write_root = write_root.expanduser().resolve() if write_root is not None else None
        self._deny_names: tuple[str, ...] = tuple(read_deny_names)
        self._deny_roots: tuple[Path, ...] = tuple(Path(r).expanduser().resolve() for r in read_deny_roots)

    @property
    def write_root(self) -> Path | None:
        return self._write_root

    def _resolve(self, path: str) -> Path:
        # strict=False allows validating paths for files that don't exist yet (e.g. pre-creation checks)
        return Path(path).expanduser().resolve(strict=False)

    def _is_denied(self, resolved: Path) -> bool:
        if any(fnmatch(resolved.name, pat) for pat in self._deny_names):
            return True
        return any(resolved.is_relative_to(root) for root in self._deny_roots)

    def assert_readable(self, path: str) -> None:
        resolved = self._resolve(path)
        if self._is_denied(resolved):
            raise FileAccessError(f"Read denied by policy: {resolved}")

    def assert_writable(self, path: str) -> None:
        resolved = self._resolve(path)
        if self._is_denied(resolved):
            raise FileAccessError(f"Write denied by policy: {resolved}")
        if self._write_root is not None and not resolved.is_relative_to(self._write_root):
            raise FileAccessError(f"Write denied: {resolved} is outside write root {self._write_root}")
