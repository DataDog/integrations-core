# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A single seam for the filesystem and subprocess operations integrations
perform on config-derived paths.

Every method is a thin passthrough preceded by a validator hook. Parity is the
hard requirement: under the default :class:`NoOpValidator`, exception types and
timing, permission bits, encodings, laziness, and return values match the
operation being replaced.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
from typing import IO, Any, Protocol, Sequence, runtime_checkable

from datadog_checks.base.utils.models.validation.security import SecurityConfig
from datadog_checks.base.utils.subprocess_output import get_subprocess_output as _base_get_subprocess_output

StrPath = str | os.PathLike[str]


def _resolve_program(program: str) -> str:
    """Resolve a bare command name the way the OS will, via PATH.

    A bare name is not a path, so the allowlist would realpath it against the
    working directory and reject every such invocation. Names containing a
    separator, and names PATH cannot resolve, are returned unchanged; an
    unresolvable name then fails the allowlist rather than being waved through.
    """
    if os.sep in program or (os.altsep and os.altsep in program):
        return program
    return shutil.which(program) or program


@runtime_checkable
class OSValidator(Protocol):
    """Enforcement seam. Implementations raise ``PermissionError`` to deny."""

    def check_path(self, path: StrPath, mode: str) -> None: ...

    def check_exec(self, argv: Sequence[str]) -> None: ...


class NoOpValidator:
    """Allows everything. Guarantees byte-identical parity with direct stdlib calls."""

    def check_path(self, path: StrPath, mode: str) -> None:
        return None

    def check_exec(self, argv: Sequence[str]) -> None:
        return None


class TrustedProviderValidator:
    """Applies the existing trusted-provider policy at the point of use.

    Invents no policy: reuses :class:`SecurityConfig` exactly as load-time field
    validation does. The only difference is *when* it runs, so runtime-derived
    paths are covered too.

    Gated by the existing ``ignore_untrusted_file_params`` setting, so enabling
    that begins enforcing at every migrated call site as well as at load time.
    There is no separate switch and no dry-run mode.
    """

    def __init__(self, security: SecurityConfig):
        self._security = security

    def _allowed(self, path: StrPath) -> bool:
        if not self._security.is_enabled():
            return True
        if self._security.is_check_excluded(self._security.check_name):
            return True
        if self._security.is_provider_trusted(self._security.provider):
            return True
        return self._security.is_file_path_allowed(os.fspath(path))

    def check_path(self, path: StrPath, mode: str) -> None:
        target = os.fspath(path)
        if not self._allowed(target):
            raise PermissionError(f"Path '{target}' is not allowed from untrusted provider '{self._security.provider}'")

    def check_exec(self, argv: Sequence[str]) -> None:
        for target in _exec_targets(argv):
            program = _resolve_program(target)
            if not self._allowed(program):
                raise PermissionError(
                    f"Executable '{program}' is not allowed from untrusted provider '{self._security.provider}'"
                )


# Programs that launch another program named later in the same argv. Checking
# only argv[0] would miss it: ceph builds `sudo {ceph_cmd}`, glusterfs builds
# `sudo {gstatus_cmd}`, and network prepends `sudo` to a conntrack path.
_EXEC_WRAPPERS = frozenset({'sudo'})

# sudo short options that consume the following argument.
_SUDO_VALUE_SHORT = frozenset('CDghpRrTtUu')

# sudo long options that consume the following argument, unless given as --opt=value.
_SUDO_VALUE_LONG = frozenset(
    {
        '--chdir',
        '--chroot',
        '--close-from',
        '--command-timeout',
        '--group',
        '--host',
        '--other-user',
        '--prompt',
        '--role',
        '--type',
        '--user',
    }
)

# sudo options that make sudo run a shell instead of a named program.
_SUDO_SHELL_OPTIONS = frozenset({'-i', '-s', '--login', '--shell'})


def _sudo_target(argv: Sequence[str]) -> "str | None":
    """Return the program ``sudo`` will launch, or ``None`` if not statically known.

    Mirrors sudo's option parsing enough to locate the command token. Returns
    ``None`` for a shell (``-i``/``-s``) or when no command follows; the wrapper
    itself is still validated by the caller.
    """
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == '--':
            index += 1
            break
        if arg.startswith('--'):
            name = arg.split('=', 1)[0]
            if name in _SUDO_SHELL_OPTIONS:
                return None
            if '=' not in arg and name in _SUDO_VALUE_LONG:
                index += 1
            index += 1
            continue
        if arg.startswith('-') and len(arg) > 1:
            # Short options may be clustered, e.g. `-nu someuser`.
            consumes_next = False
            for position, letter in enumerate(arg[1:], start=1):
                if f'-{letter}' in _SUDO_SHELL_OPTIONS:
                    return None
                if letter in _SUDO_VALUE_SHORT:
                    # Takes the rest of the cluster, or the next argument.
                    consumes_next = position == len(arg) - 1
                    break
            index += 2 if consumes_next else 1
            continue
        break

    # `sudo FOO=bar cmd` — environment assignments precede the command.
    while index < len(argv) and '=' in argv[index] and not argv[index].startswith('='):
        index += 1

    return argv[index] if index < len(argv) else None


def _exec_targets(argv: Sequence[str]) -> list[str]:
    """Return every program the argv will launch, wrapper included.

    Shell wrappers (``sh -c '...'``) are deliberately not unwrapped: what a shell
    string runs cannot be known without shell parsing, so those sites are
    validated on the shell binary only and counted as unguarded.
    """
    if not argv:
        return []
    targets = [argv[0]]
    if os.path.basename(argv[0]) in _EXEC_WRAPPERS:
        wrapped = _sudo_target(argv)
        if wrapped is not None:
            targets.append(wrapped)
    return targets


def _shell_exec_argv(command: "str | Sequence[str]") -> list[str]:
    """Return the argv the OS actually launches for a ``shell=True`` call.

    The program executed is the shell, not the first token of the command;
    validating that token would report on a program that never runs. Mirrors
    subprocess: ``/bin/sh -c`` on POSIX, ``%COMSPEC% /c`` on Windows.
    """
    if os.name == 'nt':
        shell = os.environ.get('COMSPEC', 'cmd.exe')
        flag = '/c'
    else:
        shell = '/bin/sh'
        flag = '-c'
    if isinstance(command, (str, bytes, os.PathLike)):
        return [shell, flag, os.fspath(command)]
    # With a sequence, args[0] is the command string and the rest are the
    # shell's own arguments.
    return [shell, flag, *(os.fspath(part) for part in command)]


def _exec_argv(command: "str | Sequence[str]") -> list[str]:
    """Normalize a subprocess command to an argv list for validation.

    Mirrors how the command is interpreted with ``shell=False``: a string is
    split on whitespace (matching ``get_subprocess_output``), a sequence is
    taken as-is.
    """
    if isinstance(command, (str, bytes, os.PathLike)):
        return os.fspath(command).split() if isinstance(command, str) else [os.fspath(command)]
    return list(command)


# Flags that indicate a write-intent os.open; used only to label the validator call.
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


class OSWrapper:
    """Validated passthrough over direct filesystem and subprocess operations."""

    def __init__(self, validator: OSValidator | None = None):
        self._validator: OSValidator = validator or NoOpValidator()

    def open(self, path: StrPath, mode: str = "r", *args: Any, **kwargs: Any) -> IO:
        self._validator.check_path(path, mode)
        return open(path, mode, *args, **kwargs)

    def os_open(self, path: StrPath, flags: int, mode: int = 0o777, *, dir_fd: "int | None" = None) -> int:
        access = "w" if flags & _WRITE_FLAGS else "r"
        self._validator.check_path(path, access)
        return os.open(path, flags, mode, dir_fd=dir_fd)

    def exists(self, path: StrPath) -> bool:
        self._validator.check_path(path, "r")
        return os.path.exists(path)

    def isfile(self, path: StrPath) -> bool:
        self._validator.check_path(path, "r")
        return os.path.isfile(path)

    def isdir(self, path: StrPath) -> bool:
        self._validator.check_path(path, "r")
        return os.path.isdir(path)

    def islink(self, path: StrPath) -> bool:
        self._validator.check_path(path, "r")
        return os.path.islink(path)

    def getsize(self, path: StrPath) -> int:
        self._validator.check_path(path, "r")
        return os.path.getsize(path)

    def access(self, path: StrPath, mode: int) -> bool:
        self._validator.check_path(path, "r")
        return os.access(path, mode)

    def stat(self, path: StrPath, *, follow_symlinks: bool = True) -> os.stat_result:
        self._validator.check_path(path, "r")
        return os.stat(path, follow_symlinks=follow_symlinks)

    def listdir(self, path: StrPath = ".") -> list[str]:
        self._validator.check_path(path, "r")
        return os.listdir(path)

    def scandir(self, path: StrPath = "."):
        self._validator.check_path(path, "r")
        return os.scandir(path)

    def glob(self, pathname: StrPath, **kwargs: Any) -> list[str]:
        # The pattern is validated as given; the allowlist is a prefix check, so
        # a pattern's literal leading directories satisfy or fail it as a whole.
        # Only supplied keywords are forwarded, so the call reaching glob.glob is
        # the one the caller wrote.
        self._validator.check_path(pathname, "r")
        return glob.glob(pathname, **kwargs)

    def walk(self, top: StrPath, topdown: bool = True, onerror=None, followlinks: bool = False):
        # NOTE: not a generator function on purpose. os.walk is itself lazy;
        # returning it directly preserves that laziness while keeping the
        # validator check eager (at call time), matching how a bare os.walk(p)
        # call site behaves.
        self._validator.check_path(top, "r")
        return os.walk(top, topdown=topdown, onerror=onerror, followlinks=followlinks)

    def realpath(self, path: StrPath, *, strict: bool = False) -> str:
        self._validator.check_path(path, "r")
        return os.path.realpath(path, strict=strict)

    # Alias used at sites that hand a validated path to a third-party library
    # that opens it itself (psutil, ssl, duckdb, fdb) and where the resolved
    # form is wanted.
    resolve_path = realpath

    def validate_path(self, path: StrPath, mode: str = "r") -> StrPath:
        """Validate a path and return it unchanged, for third-party handoffs.

        Prefer this over :meth:`resolve_path` when the library must receive
        exactly what the caller supplied: normalizing rewrites a relative path to
        an absolute one, which breaks parity.
        """
        self._validator.check_path(path, mode)
        return path

    def which(self, cmd: str, mode: int = os.F_OK | os.X_OK, path: "str | None" = None) -> "str | None":
        self._validator.check_exec([cmd])
        return shutil.which(cmd, mode=mode, path=path)

    def copy(self, src: StrPath, dst: StrPath, *, follow_symlinks: bool = True) -> str:
        self._validator.check_path(src, "r")
        self._validator.check_path(dst, "w")
        return shutil.copy(src, dst, follow_symlinks=follow_symlinks)

    @staticmethod
    def _launched_argv(args, kwargs) -> list[str]:
        """What the OS will actually execute, accounting for ``shell=True``."""
        return _shell_exec_argv(args) if kwargs.get('shell') else _exec_argv(args)

    def run(self, args, **kwargs):
        self._validator.check_exec(self._launched_argv(args, kwargs))
        return subprocess.run(args, **kwargs)

    def popen(self, args, **kwargs):
        self._validator.check_exec(self._launched_argv(args, kwargs))
        return subprocess.Popen(args, **kwargs)

    def get_subprocess_output(self, command, log, raise_on_empty_output=True, log_debug=True, env=None):
        self._validator.check_exec(_exec_argv(command))
        return _base_get_subprocess_output(
            command, log, raise_on_empty_output=raise_on_empty_output, log_debug=log_debug, env=env
        )


# NO ENFORCEMENT, and named so that every call site says as much. Permanently
# bound to NoOpValidator with no injection point, for code with no check instance
# that touches only paths a config cannot influence. Anything touching a
# config-derived path or executable must use `self.os` instead.
unchecked_os = OSWrapper()
