# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import pathlib
import sys
from contextlib import contextmanager
from typing import Generator

from ddev.utils.structures import EnvVars

# There is special recognition in Mypy for `sys.platform`, not `os.name`
# https://github.com/python/cpython/blob/09d7319bfe0006d9aa3fc14833b69c24ccafdca6/Lib/pathlib.py#L957
if sys.platform == 'win32':
    _PathBase = pathlib.WindowsPath
else:
    _PathBase = pathlib.PosixPath

disk_sync = os.fsync
# https://mjtsai.com/blog/2022/02/17/apple-ssd-benchmarks-and-f_fullsync/
# https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html
if sys.platform == 'darwin':
    import fcntl

    if hasattr(fcntl, 'F_FULLFSYNC'):

        def disk_sync(fd):
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


class Path(_PathBase):
    def ensure_dir_exists(self):
        self.mkdir(parents=True, exist_ok=True)

    def ensure_parent_dir_exists(self):
        self.parent.mkdir(parents=True, exist_ok=True)

    def expand(self):
        return Path(os.path.expanduser(os.path.expandvars(self)))

    def resolve(self, strict=False) -> Path:
        # https://bugs.python.org/issue38671
        return Path(os.path.realpath(self))

    def read_text(self, encoding='utf-8', errors=None, newline=None) -> str:
        return super().read_text(encoding, errors)

    def write_text(self, *args, **kwargs) -> int:
        kwargs.setdefault('encoding', 'utf-8')
        return super().write_text(*args, **kwargs)

    def stream_lines(self, encoding='utf-8') -> Generator[str, None, None]:
        if self.exists():
            with self.open(encoding=encoding) as f:
                yield from f

    def open(self, **kwargs):
        if not kwargs.get('mode', 'r')[1:].startswith('b'):
            kwargs.setdefault('encoding', 'utf-8')

        return super().open(**kwargs)

    def remove(self):
        if self.is_file():
            os.remove(self)
        elif self.is_dir():
            import shutil

            shutil.rmtree(self, ignore_errors=False)

    def write_atomic(self, data: str | bytes, *args, **kwargs) -> None:
        from tempfile import mkstemp

        fd, path = mkstemp(dir=self.parent)
        with os.fdopen(fd, *args, **kwargs) as f:
            f.write(data)
            f.flush()
            disk_sync(fd)

        os.replace(path, self)

    @contextmanager
    def as_cwd(self, *args, **kwargs) -> Generator[Path, None, None]:
        origin = os.getcwd()
        os.chdir(self)

        try:
            if args or kwargs:
                with EnvVars(*args, **kwargs):
                    yield self
            else:
                yield self
        finally:
            os.chdir(origin)

    @contextmanager
    def temp_hide(self) -> Generator[Path, None, None]:
        with temp_directory() as temp_dir:
            temp_path = Path(temp_dir, self.name)
            try:
                self.replace(temp_dir / self.name)
            except FileNotFoundError:
                pass

            try:
                yield temp_path
            finally:
                try:
                    temp_path.replace(self)
                except FileNotFoundError:
                    pass


def pretty_path(path: str | os.PathLike[str], base: str | os.PathLike[str] | None = None) -> str:
    """Render a filesystem path as relative to base (default: cwd) when that's concise.

    Falls back to the original absolute path if the relative form would need to
    traverse more than one parent directory — in which case the absolute path is
    usually easier to read. Matches the heuristic used by ConfigFile.pretty_overrides_path.
    """
    from collections import Counter

    base_dir = os.fspath(base) if base is not None else os.getcwd()
    target = os.fspath(path)
    try:
        relative = os.path.relpath(target, base_dir)
    except ValueError:
        # Different drive on Windows — no meaningful relative path.
        return target
    parents_apart = Counter(relative.split(os.path.sep))
    if parents_apart.get("..", 0) > 1:
        return target
    return relative


@contextmanager
def temp_directory() -> Generator[Path, None, None]:
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as d:
        yield Path(d).resolve()


@contextmanager
def temp_chdir(env_vars=None) -> Generator[Path, None, None]:
    with temp_directory() as d:
        with d.as_cwd(env_vars=env_vars):
            yield d
