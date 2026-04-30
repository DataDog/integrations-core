# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path


def canonicalize_path(path: str | Path) -> Path:
    """Single source of truth for path canonicalization across the fs layer.

    Every component that compares, indexes, or operates on filesystem paths
    must run them through this function so the policy, the tools, and the
    registry agree on what path each input names.

    ``strict=False`` allows resolving paths for files that don't exist yet
    (e.g. pre-creation checks). Idempotent: calling on an already-canonical
    path returns the same path.
    """
    return Path(path).expanduser().resolve(strict=False)


_WILDCARD_CHARS = "*?["


def _canonicalize_pattern(pat: str) -> str:
    """Resolve a path pattern's static prefix while leaving wildcards intact.

    Splits at the first wildcard character (``*``, ``?`` or ``[``), runs
    expanduser + resolve on the leading prefix, then re-attaches the
    wildcard suffix. Patterns without wildcards are fully resolved. Used so
    symlinked deny roots (e.g. ``~/.ssh -> /secrets/ssh``) are matched
    against the same target the path side canonicalizes to.
    """
    indices = [pat.find(c) for c in _WILDCARD_CHARS if c in pat]
    idx = min(indices) if indices else -1
    if idx == -1:
        return str(canonicalize_path(pat))
    prefix, suffix = pat[:idx], pat[idx:]
    if not prefix:
        return suffix
    resolved = str(canonicalize_path(prefix))
    # canonicalize_path strips trailing separators; restore one if the prefix
    # had it so "<dir>/" + "*" stays "<dir>/*" instead of "<dir>*".
    if prefix.endswith(("/", os.sep)) and not resolved.endswith(("/", os.sep)):
        resolved += os.sep
    return f"{resolved}{suffix}"


DEFAULT_DENY_PATTERNS: tuple[str, ...] = (
    # Location-independent: secrets identified by name or extension.
    ".env",
    ".env.*",
    ".envrc",
    ".netrc",
    "*.pem",
    "*.key",
    # Location-rooted: entire directories of secrets.
    "~/.ssh/*",
    "~/.aws/*",
    "~/.gnupg/*",
    "~/.config/gcloud/*",
    "~/.kube/*",
    "~/.docker/*",
)


class FileAccessError(Exception):
    """Raised when a file access violates the configured policy."""


class FileAccessPolicy:
    """Global file access policy shared across agents and phases in a run.

    Enforces a two-zone model based on ``write_root``: inside it, all reads
    and writes are allowed. Outside, writes are always denied; reads are
    allowed only if the path does not match a deny pattern.

    Each entry in ``deny_patterns`` is an fnmatch-style glob. Patterns are
    classified at construction time:

    - **Basename patterns** (no ``/``) are matched against the resolved
      path's basename — they apply globally regardless of location. Use
      these for location-independent rules like ``*.pem`` or ``.env``.
    - **Path patterns** (contain ``/``) are matched against the resolved
      path's full string. Their static prefix is run through
      ``expanduser + resolve`` at construction so symlinked roots cannot
      bypass the rule. Use these for location-specific rules like
      ``~/.ssh/*`` or ``~/.aws/credentials``.

    Paths checked at runtime go through ``canonicalize_path`` before
    matching, so symlinks and ``..`` cannot bypass the checks.
    """

    def __init__(
        self,
        write_root: Path | str,
        deny_patterns: Iterable[str] = DEFAULT_DENY_PATTERNS,
    ) -> None:
        self._write_root = canonicalize_path(write_root)
        patterns = tuple(deny_patterns)
        self._deny_patterns: tuple[str, ...] = patterns

        basename: list[str] = []
        path: list[str] = []
        for p in patterns:
            (path if "/" in p else basename).append(p)
        self._basename_patterns: tuple[str, ...] = tuple(basename)
        self._path_patterns: tuple[str, ...] = tuple(_canonicalize_pattern(p) for p in path)

    @property
    def write_root(self) -> Path:
        return self._write_root

    @property
    def deny_patterns(self) -> tuple[str, ...]:
        return self._deny_patterns

    @property
    def basename_patterns(self) -> tuple[str, ...]:
        return self._basename_patterns

    def _is_denied(self, resolved: Path) -> bool:
        if any(fnmatch(resolved.name, pat) for pat in self._basename_patterns):
            return True
        full = str(resolved)
        return any(fnmatch(full, pat) for pat in self._path_patterns)

    def assert_readable(self, path: str | Path) -> Path:
        resolved = canonicalize_path(path)
        if resolved.is_relative_to(self._write_root):
            return resolved
        if self._is_denied(resolved):
            raise FileAccessError(f"Read denied by policy: {resolved}")
        return resolved

    def assert_writable(self, path: str | Path) -> Path:
        resolved = canonicalize_path(path)
        if not resolved.is_relative_to(self._write_root):
            raise FileAccessError(f"Write denied: {resolved} is outside write root {self._write_root}")
        return resolved
