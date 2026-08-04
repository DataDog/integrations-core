# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A unit-test double for :class:`~datadog_checks.base.utils.os_interface.OSInterface`.

The point of this stub is to give integration tests a *single* place to mock the
filesystem and subprocess operations a check performs, regardless of how the code
under test reaches the OS layer (the per-check ``self.os_interface`` property or
the module-level ``os_interface`` singleton). Test authors configure one object
instead of hunting for the right ``mock.patch`` target.

Every method on the double is a :class:`unittest.mock.MagicMock`, so the full
mock vocabulary keeps working unchanged: ``return_value``, ``side_effect`` (both
scalars and lists), ``assert_called_with``/``assert_any_call``, ``call_count``,
and so on. On top of that, declarative helpers wire an in-memory filesystem and a
command registry into the read/subprocess methods for the common cases:

    fake = MockOSInterface()
    fake.add_file("/sys/class/infiniband/mlx5_0/ports/1/rate", "100 Gb/sec")
    fake.add_dir("/sys/class/infiniband/mlx5_0/ports")
    fake.set_command_output("netstat -i", stdout="...", returncode=0)

Anything not configured behaves like a bare ``MagicMock``. Use the fixture
``mock_os_interface`` (from the ``datadog_checks.dev`` pytest plugin) to install
one of these at both seams for the duration of a test.
"""

from __future__ import annotations

import errno
import io
import os
import subprocess
from unittest import mock

# The public method surface of OSInterface. Kept in sync with that class; the
# fixture uses this list to patch the singleton, and __init__ uses it to create
# one MagicMock per method.
METHOD_NAMES = (
    "open",
    "os_open",
    "exists",
    "isfile",
    "isdir",
    "islink",
    "getsize",
    "access",
    "stat",
    "listdir",
    "scandir",
    "walk",
    "realpath",
    "resolve_path",
    "which",
    "copy",
    "run",
    "popen",
    "get_subprocess_output",
)

# Methods whose default behavior is backed by the in-memory filesystem once a
# declarative helper (add_file/add_dir/...) has populated it.
_FS_METHODS = (
    "open",
    "exists",
    "isfile",
    "isdir",
    "islink",
    "getsize",
    "listdir",
    "scandir",
    "walk",
)


class DirEntry:
    """Minimal stand-in for :class:`os.DirEntry` as returned by ``scandir``."""

    def __init__(self, name: str, path: str, is_dir: bool):
        self.name = name
        self.path = path
        self._is_dir = is_dir

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return self._is_dir

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return not self._is_dir

    def is_symlink(self) -> bool:
        return False


class _ScandirResult:
    """Context-manager iterable mirroring the object returned by ``os.scandir``."""

    def __init__(self, entries: list[DirEntry]):
        self._entries = entries

    def __iter__(self):
        return iter(self._entries)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self) -> None:
        self._entries = []


class _CapturingText(io.StringIO):
    """Text buffer that writes its contents back to the fake filesystem on close."""

    def __init__(self, store: dict, path: str, initial: str = ""):
        super().__init__(initial)
        self.seek(len(initial))
        self._store = store
        self._path = path

    def close(self) -> None:
        if not self.closed:
            self._store[self._path] = self.getvalue()
        super().close()


class _CapturingBytes(io.BytesIO):
    """Binary counterpart of :class:`_CapturingText`."""

    def __init__(self, store: dict, path: str, initial: bytes = b""):
        super().__init__(initial)
        self.seek(len(initial))
        self._store = store
        self._path = path

    def close(self) -> None:
        if not self.closed:
            self._store[self._path] = self.getvalue()
        super().close()


def _normalize_command(command) -> str:
    """Render a subprocess command to a stable string key.

    Matches how a call site passes the command: a string is used verbatim, a
    sequence is joined on single spaces.
    """
    if isinstance(command, (str, bytes, os.PathLike)):
        return os.fspath(command) if not isinstance(command, bytes) else command.decode()
    return " ".join(os.fspath(part) if isinstance(part, os.PathLike) else str(part) for part in command)


class MockOSInterface:
    """Configurable test double whose methods are MagicMocks.

    Populate it declaratively with :meth:`add_file`, :meth:`add_dir`, and
    :meth:`set_command_output`, or drive the underlying mocks directly
    (``fake.exists.return_value = True``, ``fake.popen.side_effect = [...]``).
    """

    def __init__(self):
        # In-memory filesystem: path -> contents (str or bytes) for files; a set
        # of directory paths. Parent directories are registered implicitly.
        self._files: dict[str, str | bytes] = {}
        self._dirs: set[str] = set()
        self._links: dict[str, str] = {}
        # command key -> (stdout, stderr, returncode)
        self._commands: dict[str, tuple] = {}

        for name in METHOD_NAMES:
            setattr(self, name, mock.MagicMock(name=name))

        # Filesystem methods are backed by the (initially empty) in-memory store
        # from the start, so an unconfigured read behaves realistically: opening
        # or listing a path that was never added raises FileNotFoundError, and a
        # write is captured. Subprocess methods stay bare MagicMocks until
        # set_command_output is called, so plain return_value/side_effect usage
        # keeps working out of the box.
        self._wire_filesystem()

    # -- declarative filesystem setup ------------------------------------- #
    def add_file(self, path: str | os.PathLike, content: str | bytes = "") -> None:
        """Register a file with the given contents and wire the FS methods."""
        p = self._norm(path)
        self._files[p] = content
        self._register_parents(p)
        self._wire_filesystem()

    def add_files(self, mapping: dict) -> None:
        for path, content in mapping.items():
            self.add_file(path, content)

    def add_dir(self, path: str | os.PathLike) -> None:
        """Register a directory (and its parents) and wire the FS methods."""
        p = self._norm(path)
        self._dirs.add(p)
        self._register_parents(p)
        self._wire_filesystem()

    def add_symlink(self, path: str | os.PathLike, target: str | os.PathLike = "") -> None:
        p = self._norm(path)
        self._links[p] = self._norm(target) if target else ""
        self._register_parents(p)
        self._wire_filesystem()

    def get_file(self, path: str | os.PathLike) -> str | bytes:
        """Return current contents of a file (including writes captured via open)."""
        return self._files[self._norm(path)]

    # -- declarative subprocess setup ------------------------------------- #
    def set_command_output(self, command, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        """Register output for a command, consumed by get_subprocess_output and run."""
        self._commands[_normalize_command(command)] = (stdout, stderr, returncode)
        self.get_subprocess_output.side_effect = self._get_subprocess_output_impl
        self.run.side_effect = self._run_impl

    # -- internals -------------------------------------------------------- #
    @staticmethod
    def _norm(path: str | os.PathLike) -> str:
        p = os.fspath(path)
        # Preserve root "/" but drop a single trailing slash elsewhere.
        return p if p == "/" else p.rstrip("/")

    def _register_parents(self, path: str) -> None:
        parent = os.path.dirname(path)
        while parent and parent not in self._dirs:
            self._dirs.add(parent)
            if parent in ("/", os.path.dirname(parent)):
                break
            parent = os.path.dirname(parent)

    def _wire_filesystem(self) -> None:
        # Idempotent: rebind each FS method's side_effect to the store-backed impl.
        self.open.side_effect = self._open_impl
        self.exists.side_effect = lambda p: self._norm(p) in self._files or self._norm(p) in self._dirs
        self.isfile.side_effect = lambda p: self._norm(p) in self._files
        self.isdir.side_effect = lambda p: self._norm(p) in self._dirs
        self.islink.side_effect = lambda p: self._norm(p) in self._links
        self.getsize.side_effect = self._getsize_impl
        self.listdir.side_effect = self._listdir_impl
        self.scandir.side_effect = self._scandir_impl
        self.walk.side_effect = self._walk_impl

    def _open_impl(self, path, mode="r", *args, **kwargs):
        p = self._norm(path)
        binary = "b" in mode
        writing = any(flag in mode for flag in ("w", "a", "x"))
        if writing:
            appending = "a" in mode
            if binary:
                initial = self._files.get(p, b"") if appending else b""
                if isinstance(initial, str):
                    initial = initial.encode("utf-8")
                return _CapturingBytes(self._files, p, initial)
            initial = self._files.get(p, "") if appending else ""
            if isinstance(initial, bytes):
                initial = initial.decode("utf-8")
            return _CapturingText(self._files, p, initial)
        if p not in self._files:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), p)
        content = self._files[p]
        if binary:
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            return io.BytesIO(data)
        data = content.decode("utf-8") if isinstance(content, bytes) else content
        return io.StringIO(data)

    def _getsize_impl(self, path):
        p = self._norm(path)
        if p not in self._files:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), p)
        content = self._files[p]
        return len(content if isinstance(content, bytes) else content.encode("utf-8"))

    def _children(self, path: str):
        for entry in list(self._files) + list(self._dirs):
            if os.path.dirname(entry) == path and entry != path:
                yield entry

    def _listdir_impl(self, path="."):
        p = self._norm(path)
        if p not in self._dirs:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), p)
        return sorted({os.path.basename(child) for child in self._children(p)})

    def _scandir_impl(self, path="."):
        p = self._norm(path)
        if p not in self._dirs:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), p)
        entries = [
            DirEntry(os.path.basename(child), child, is_dir=child in self._dirs) for child in sorted(self._children(p))
        ]
        return _ScandirResult(entries)

    def _walk_impl(self, top, topdown=True, onerror=None, followlinks=False):
        top = self._norm(top)
        results = []

        def visit(current):
            children = sorted(self._children(current))
            dirnames = [os.path.basename(c) for c in children if c in self._dirs]
            filenames = [os.path.basename(c) for c in children if c in self._files]
            entry = (current, dirnames, filenames)
            if topdown:
                results.append(entry)
            for name in dirnames:
                visit(os.path.join(current, name))
            if not topdown:
                results.append(entry)

        if top in self._dirs:
            visit(top)
        return iter(results)

    def _get_subprocess_output_impl(self, command, *args, **kwargs):
        key = _normalize_command(command)
        if key not in self._commands:
            raise KeyError(f"No command output registered for {key!r}")
        return self._commands[key]

    def _run_impl(self, args, **kwargs):
        key = _normalize_command(args)
        stdout, stderr, returncode = self._commands.get(key, ("", "", 0))
        text = kwargs.get("text") or kwargs.get("universal_newlines")
        if not text:
            stdout = stdout.encode("utf-8") if isinstance(stdout, str) else stdout
            stderr = stderr.encode("utf-8") if isinstance(stderr, str) else stderr
        return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)
