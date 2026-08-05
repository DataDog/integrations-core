# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A single seam for the direct filesystem and subprocess operations that
integrations perform on config-derived paths.

Every method is a thin passthrough to the stdlib call it replaces, preceded by
a validator hook. With the default :class:`NoOpValidator` the behavior is
byte-identical to calling the stdlib directly; a check that injects a real
validator (see :class:`~datadog_checks.base.utils.models.validation.security`)
gets its config-derived paths and executables checked at the point of use,
regardless of where the path was derived.

The hard requirement is parity: under the no-op validator, exception types and
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

    A bare name such as ``sudo``, ``gunicorn`` or ``lsid`` is not a path: the
    allowlist check would realpath it against the working directory and reject
    every such invocation. The program that will actually run is the one PATH
    resolves to, so that is what gets validated. Names that already contain a
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

    This validator invents no allowlist policy of its own. It reuses
    :class:`SecurityConfig` exactly as the config-load-time field validation
    does: enforcement off, an excluded check, or a trusted provider all pass
    through; otherwise the resolved path (or executable path) must fall under a
    configured allowlist prefix. The only difference from the load-time check is
    *when* it runs: at the actual file/exec operation, so runtime-derived paths
    are covered too.

    Enforcement is gated by the existing ``ignore_untrusted_file_params`` setting,
    the same switch that governs config-field validation. Turning that on
    therefore begins enforcing at every migrated call site as well as at load
    time; there is no separate switch and no dry-run mode.
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


# Programs that launch another program named later in the same argv. Validating
# only argv[0] would check the wrapper and miss the program actually executed:
# ceph builds `sudo {ceph_cmd}`, glusterfs builds `sudo {gstatus_cmd}`, and the
# network check prepends `sudo` to a config-derived conntrack path.
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
    """Return the program ``sudo`` will launch, or ``None`` if it is not statically known.

    Mirrors sudo's own argument parsing closely enough to locate the command
    token: options are skipped (consuming a value where sudo takes one), ``--``
    ends option parsing, and leading ``VAR=value`` environment assignments are
    skipped. Returns ``None`` when sudo is asked to run a shell (``-i``/``-s``)
    or when no command token follows, since there is then no program name to
    validate; the wrapper itself is still validated by the caller.
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
                    # A value-taking letter takes the rest of the cluster as its
                    # value, or the next argument when it ends the cluster.
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

    NOTE: shell wrappers (``sh -c '...'``) are deliberately not unwrapped. The
    program a shell string runs cannot be determined without implementing shell
    parsing, so those sites are validated on the shell binary only and are
    documented as unguarded rather than given a false sense of coverage.
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

    With ``shell=True`` the program executed is the shell, not the first token of
    the command; validating that token would report on a program that never runs.
    Mirrors subprocess: POSIX runs ``/bin/sh -c <command>``, Windows runs
    ``%COMSPEC% /c <command>``. Since ``_exec_targets`` does not unwrap shell
    strings, the effect is that the shell binary is what gets validated.
    """
    if os.name == 'nt':
        shell = os.environ.get('COMSPEC', 'cmd.exe')
        flag = '/c'
    else:
        shell = '/bin/sh'
        flag = '-c'
    if isinstance(command, (str, bytes, os.PathLike)):
        return [shell, flag, os.fspath(command)]
    # POSIX shell=True with a sequence: args[0] is the command string and the
    # remainder become the shell's own arguments.
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


class OSInterface:
    """Validated passthrough over direct filesystem and subprocess operations."""

    def __init__(self, validator: OSValidator | None = None):
        self._validator: OSValidator = validator or NoOpValidator()

    # -- open / raw fd ----------------------------------------------------- #
    def open(self, path: StrPath, mode: str = "r", *args: Any, **kwargs: Any) -> IO:
        self._validator.check_path(path, mode)
        return open(path, mode, *args, **kwargs)

    def os_open(self, path: StrPath, flags: int, mode: int = 0o777, *, dir_fd: "int | None" = None) -> int:
        access = "w" if flags & _WRITE_FLAGS else "r"
        self._validator.check_path(path, access)
        return os.open(path, flags, mode, dir_fd=dir_fd)

    # -- predicates -------------------------------------------------------- #
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

    # -- listing ----------------------------------------------------------- #
    def listdir(self, path: StrPath = ".") -> list[str]:
        self._validator.check_path(path, "r")
        return os.listdir(path)

    def scandir(self, path: StrPath = "."):
        self._validator.check_path(path, "r")
        return os.scandir(path)

    def glob(self, pathname: StrPath, **kwargs: Any) -> list[str]:
        # The pattern itself is what the caller supplied, so it is what gets
        # validated; the allowlist is a prefix check, which a pattern's literal
        # leading directories still satisfy or fail as a whole.
        #
        # Only explicitly supplied keywords are forwarded, so the call reaching
        # glob.glob is the one the caller wrote. Injecting defaults here would
        # change the observable call and break callers that wrap or patch it.
        self._validator.check_path(pathname, "r")
        return glob.glob(pathname, **kwargs)

    def walk(self, top: StrPath, topdown: bool = True, onerror=None, followlinks: bool = False):
        # NOTE: not a generator function on purpose. os.walk is itself lazy;
        # returning it directly preserves that laziness while keeping the
        # validator check eager (at call time), matching how a bare os.walk(p)
        # call site behaves.
        self._validator.check_path(top, "r")
        return os.walk(top, topdown=topdown, onerror=onerror, followlinks=followlinks)

    # -- path resolution / lookup ----------------------------------------- #
    def realpath(self, path: StrPath, *, strict: bool = False) -> str:
        self._validator.check_path(path, "r")
        return os.path.realpath(path, strict=strict)

    # Alias used at sites that hand a validated path to a third-party library
    # that opens it itself (psutil, ssl, duckdb, fdb) and where the resolved
    # form is wanted.
    resolve_path = realpath

    def validate_path(self, path: StrPath, mode: str = "r") -> StrPath:
        """Validate a path and return it unchanged, for third-party handoffs.

        Use this instead of :meth:`resolve_path` when the library must receive
        exactly what the caller supplied. ``resolve_path`` normalizes, which
        rewrites a relative path to an absolute one and so changes the value the
        library sees; that breaks parity with passing the raw path through.
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

    # -- subprocess family ------------------------------------------------- #
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


# Module-level default: NO ENFORCEMENT, byte-identical to the stdlib.
#
# This singleton is permanently bound to NoOpValidator and has no injection
# point, so a validator can never be attached to it. It exists only for sites
# that operate on paths a config cannot influence (bundled assets, hardcoded
# system paths) and that have no check instance to reach.
#
# Any site that touches a config-derived path or executable MUST use the
# validator-bound interface, AgentCheck.os_interface, or enforcement silently
# does nothing there. Module-level helpers that need it should take the
# interface as a parameter and be called with `self.os_interface`.
os_interface = OSInterface()
