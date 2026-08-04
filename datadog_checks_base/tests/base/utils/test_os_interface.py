# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Parity + enforcement tests for the OS abstraction layer.

The hard requirement is byte-identical behavior versus the stdlib when the
default (no-op) validator is used. Each test compares the interface against the
raw ``os``/``open``/``subprocess`` call it replaces.
"""

import os
import stat
import subprocess
from unittest import mock

import pytest

from datadog_checks.base.utils.models.validation.security import SecurityConfig
from datadog_checks.base.utils.os_interface import (
    NoOpValidator,
    OSInterface,
    TrustedProviderValidator,
    os_interface,
)


@pytest.fixture
def osx():
    return OSInterface()


class RecordingValidator:
    """Validator that records calls and can be told to deny."""

    def __init__(self, deny_paths=(), deny_execs=()):
        self.deny_paths = set(deny_paths)
        self.deny_execs = set(deny_execs)
        self.path_calls = []
        self.exec_calls = []

    def check_path(self, path, mode):
        self.path_calls.append((os.fspath(path), mode))
        if os.fspath(path) in self.deny_paths:
            raise PermissionError(os.fspath(path))

    def check_exec(self, argv):
        argv = list(argv)
        self.exec_calls.append(argv)
        if argv and argv[0] in self.deny_execs:
            raise PermissionError(argv[0])


# --------------------------------------------------------------------------- #
# open / raw fd
# --------------------------------------------------------------------------- #
def test_open_default_mode_is_read(osx, tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello")
    with osx.open(str(p)) as f:
        assert f.read() == "hello"
        assert f.mode == "r"


def test_open_read_write_roundtrip(osx, tmp_path):
    p = tmp_path / "f.txt"
    with osx.open(str(p), "w") as f:
        f.write("data")
    with osx.open(str(p)) as f:
        assert f.read() == "data"


def test_open_created_file_permission_bits_match_builtin(osx, tmp_path):
    # Regression guard: the earlier prototype wired a custom opener that called
    # os.open() without a mode, producing 0o777-derived bits instead of
    # builtin open()'s 0o666-derived bits. Created files must match builtin open.
    ref = tmp_path / "ref.txt"
    with open(str(ref), "w") as f:
        f.write("x")
    got = tmp_path / "got.txt"
    with osx.open(str(got), "w") as f:
        f.write("x")
    assert stat.S_IMODE(os.stat(got).st_mode) == stat.S_IMODE(os.stat(ref).st_mode)


def test_open_binary_mode(osx, tmp_path):
    p = tmp_path / "b.bin"
    with osx.open(str(p), "wb") as f:
        f.write(b"\x00\x01")
    with osx.open(str(p), "rb") as f:
        assert f.read() == b"\x00\x01"


def test_open_missing_file_raises_same_exception(osx, tmp_path):
    missing = str(tmp_path / "nope.txt")
    with pytest.raises(FileNotFoundError):
        osx.open(missing)


def test_open_encoding_passthrough(osx, tmp_path):
    p = tmp_path / "u.txt"
    with osx.open(str(p), "w", encoding="utf-8") as f:
        f.write("café")
    with osx.open(str(p), encoding="utf-8") as f:
        assert f.read() == "café"


def test_os_open_raw_fd_roundtrip(osx, tmp_path):
    p = tmp_path / "raw.txt"
    fd = osx.os_open(str(p), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.write(fd, b"z")
    finally:
        os.close(fd)
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert p.read_bytes() == b"z"


# --------------------------------------------------------------------------- #
# predicates
# --------------------------------------------------------------------------- #
def test_predicates_match_stdlib(osx, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("123")
    d = tmp_path / "sub"
    d.mkdir()
    missing = tmp_path / "missing"

    for target in (f, d, missing):
        s = str(target)
        assert osx.exists(s) == os.path.exists(s)
        assert osx.isfile(s) == os.path.isfile(s)
        assert osx.isdir(s) == os.path.isdir(s)
        assert osx.islink(s) == os.path.islink(s)

    assert osx.getsize(str(f)) == os.path.getsize(str(f))
    assert osx.access(str(f), os.R_OK) == os.access(str(f), os.R_OK)


def test_stat_matches_stdlib(osx, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("123")
    assert osx.stat(str(f)).st_size == os.stat(str(f)).st_size


def test_getsize_missing_raises(osx, tmp_path):
    with pytest.raises(OSError):
        osx.getsize(str(tmp_path / "missing"))


# --------------------------------------------------------------------------- #
# listing
# --------------------------------------------------------------------------- #
def test_listdir_matches_stdlib(osx, tmp_path):
    (tmp_path / "a").write_text("")
    (tmp_path / "b").write_text("")
    assert sorted(osx.listdir(str(tmp_path))) == sorted(os.listdir(str(tmp_path)))


def test_scandir_matches_stdlib(osx, tmp_path):
    (tmp_path / "a").write_text("")
    (tmp_path / "b").write_text("")
    with osx.scandir(str(tmp_path)) as it:
        names = sorted(e.name for e in it)
    assert names == sorted(os.listdir(str(tmp_path)))


def test_walk_matches_stdlib_and_is_lazy(osx, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f").write_text("")
    got = {(r, tuple(sorted(d)), tuple(sorted(f))) for r, d, f in osx.walk(str(tmp_path))}
    ref = {(r, tuple(sorted(d)), tuple(sorted(f))) for r, d, f in os.walk(str(tmp_path))}
    assert got == ref


def test_walk_on_missing_path_yields_nothing_like_stdlib(osx, tmp_path):
    missing = str(tmp_path / "missing")
    assert list(osx.walk(missing)) == list(os.walk(missing))


# --------------------------------------------------------------------------- #
# path resolution / lookup
# --------------------------------------------------------------------------- #
def test_realpath_matches_stdlib(osx, tmp_path):
    p = str(tmp_path / "x")
    assert osx.realpath(p) == os.path.realpath(p)
    assert osx.resolve_path(p) == os.path.realpath(p)


def test_which_matches_stdlib(osx):
    import shutil

    assert osx.which("sh") == shutil.which("sh")
    assert osx.which("this-binary-does-not-exist-xyz") is None


def test_copy_matches_stdlib(osx, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dst = tmp_path / "dst.txt"
    osx.copy(str(src), str(dst))
    assert dst.read_text() == "payload"


# --------------------------------------------------------------------------- #
# subprocess family
# --------------------------------------------------------------------------- #
def test_run_passthrough(osx):
    result = osx.run(["echo", "hi"], capture_output=True, text=True)
    ref = subprocess.run(["echo", "hi"], capture_output=True, text=True)
    assert result.stdout == ref.stdout == "hi\n"
    assert result.returncode == 0


def test_popen_passthrough(osx):
    proc = osx.popen(["echo", "hi"], stdout=subprocess.PIPE, text=True)
    out, _ = proc.communicate()
    assert out == "hi\n"
    assert proc.returncode == 0


def test_get_subprocess_output_passthrough(osx):
    import logging

    log = logging.getLogger("test")
    out, err, code = osx.get_subprocess_output(["echo", "hi"], log)
    assert out.strip() == "hi"
    assert code == 0


# --------------------------------------------------------------------------- #
# validator enforcement
# --------------------------------------------------------------------------- #
def test_validator_invoked_on_path_ops(tmp_path):
    v = RecordingValidator()
    osx = OSInterface(v)
    f = tmp_path / "a.txt"
    f.write_text("x")
    osx.exists(str(f))
    osx.isfile(str(f))
    with osx.open(str(f)):
        pass
    modes = {mode for _, mode in v.path_calls}
    assert v.path_calls  # validator was consulted
    assert "r" in modes


def test_validator_can_deny_path(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    v = RecordingValidator(deny_paths={str(f)})
    osx = OSInterface(v)
    with pytest.raises(PermissionError):
        osx.open(str(f))
    # denial happens before the real call: file is never opened
    assert v.path_calls == [(str(f), "r")]


def test_open_write_mode_reported_to_validator(tmp_path):
    v = RecordingValidator()
    osx = OSInterface(v)
    with osx.open(str(tmp_path / "w.txt"), "w"):
        pass
    assert (str(tmp_path / "w.txt"), "w") in v.path_calls


def test_validator_invoked_on_exec(osx=None):
    v = RecordingValidator()
    osx = OSInterface(v)
    osx.run(["echo", "hi"], capture_output=True)
    assert v.exec_calls == [["echo", "hi"]]


def test_validator_can_deny_exec():
    v = RecordingValidator(deny_execs={"echo"})
    osx = OSInterface(v)
    with pytest.raises(PermissionError):
        osx.run(["echo", "hi"], capture_output=True)
    assert v.exec_calls == [["echo", "hi"]]


def test_exec_string_command_validated_as_argv0():
    v = RecordingValidator()
    osx = OSInterface(v)
    # get_subprocess_output accepts a whitespace-split string command
    import logging

    osx.get_subprocess_output("echo hi", logging.getLogger("t"))
    assert v.exec_calls[0][0] == "echo"


# --------------------------------------------------------------------------- #
# module-level default singleton
# --------------------------------------------------------------------------- #
def test_module_singleton_is_noop(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text("ok")
    assert os_interface.exists(str(p)) is True
    with os_interface.open(str(p)) as f:
        assert f.read() == "ok"


def test_noop_validator_returns_none():
    v = NoOpValidator()
    assert v.check_path("/anything", "r") is None
    assert v.check_exec(["/bin/anything"]) is None


# --------------------------------------------------------------------------- #
# TrustedProviderValidator: delegates to SecurityConfig, no new policy
# --------------------------------------------------------------------------- #
def test_trusted_provider_disabled_allows_everything(tmp_path):
    # enforcement off (default): identical to no-op
    sec = SecurityConfig(check_name="c", provider="untrusted", ignore_untrusted_file_params=False)
    osx = OSInterface(TrustedProviderValidator(sec))
    f = tmp_path / "a.txt"
    f.write_text("x")
    with osx.open(str(f)) as fh:
        assert fh.read() == "x"


def test_trusted_provider_trusted_provider_passes(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="file",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        file_paths_allowlist=[],
    )
    osx = OSInterface(TrustedProviderValidator(sec))
    f = tmp_path / "a.txt"
    f.write_text("x")
    with osx.open(str(f)):
        pass  # trusted provider: allowed despite empty allowlist


def test_trusted_provider_untrusted_outside_allowlist_denied(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        file_paths_allowlist=[str(tmp_path / "allowed")],
    )
    osx = OSInterface(TrustedProviderValidator(sec))
    with pytest.raises(PermissionError):
        osx.open(str(f))


def test_trusted_provider_untrusted_inside_allowlist_allowed(tmp_path):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    f = allowed_dir / "a.txt"
    f.write_text("x")
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        file_paths_allowlist=[str(allowed_dir)],
    )
    osx = OSInterface(TrustedProviderValidator(sec))
    with osx.open(str(f)) as fh:
        assert fh.read() == "x"


def test_trusted_provider_excluded_check_passes(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        excluded_checks=["c"],
        file_paths_allowlist=[],
    )
    osx = OSInterface(TrustedProviderValidator(sec))
    with osx.open(str(f)):
        pass


def test_trusted_provider_gates_exec_by_binary_path(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        file_paths_allowlist=[str(tmp_path / "allowed_bin")],
    )
    osx = OSInterface(TrustedProviderValidator(sec))
    with pytest.raises(PermissionError):
        osx.run(["/usr/bin/evil", "--flag"], capture_output=True)


# --------------------------------------------------------------------------- #
# AgentCheck integration
# --------------------------------------------------------------------------- #
def test_agentcheck_exposes_bound_interface(tmp_path):
    from datadog_checks.base import AgentCheck

    check = AgentCheck("c", {}, [{}])
    assert isinstance(check.os_interface, OSInterface)
    # cached
    assert check.os_interface is check.os_interface
    # default config disables enforcement -> passthrough
    p = tmp_path / "a.txt"
    p.write_text("ok")
    assert check.os_interface.exists(str(p)) is True


# --------------------------------------------------------------------------- #
# Exec wrappers: the program sudo launches must be validated, not just argv[0].
# Regression coverage for ceph's `sudo {ceph_cmd}`, glusterfs' `sudo {gstatus_cmd}`
# and the network check prepending `sudo` to a config-derived conntrack path.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "argv, expected",
    [
        (["sudo", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["/usr/bin/sudo", "/usr/bin/evil"], ["/usr/bin/sudo", "/usr/bin/evil"]),
        (["sudo", "-u", "root", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "--user", "root", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "--user=root", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "-n", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "-nu", "root", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "--", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "FOO=bar", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        (["sudo", "-ln", "/usr/bin/evil"], ["sudo", "/usr/bin/evil"]),
        # A shell has no statically known target; only the wrapper is validated.
        (["sudo", "-s"], ["sudo"]),
        (["sudo", "-i"], ["sudo"]),
        # Nothing to unwrap.
        (["sudo"], ["sudo"]),
        (["/usr/bin/evil"], ["/usr/bin/evil"]),
        ([], []),
        # Not a wrapper: `sh -c` is deliberately not unwrapped.
        (["sh", "-c", "evil"], ["sh"]),
    ],
)
def test_exec_targets(argv, expected):
    from datadog_checks.base.utils.os_interface import _exec_targets

    assert _exec_targets(argv) == expected


def _sudo_validator(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        file_paths_allowlist=[str(tmp_path)],
    )
    return TrustedProviderValidator(sec)


def test_sudo_wrapped_binary_outside_allowlist_is_denied(tmp_path):
    v = _sudo_validator(tmp_path)
    # `sudo` itself resolves outside the allowlist, so this denies on the wrapper;
    # assert the wrapped binary is denied even when the wrapper is allowed.
    allowed_sudo = tmp_path / "sudo"
    allowed_sudo.write_text("")
    with pytest.raises(PermissionError, match="evil"):
        v.check_exec([str(allowed_sudo), "/usr/bin/evil"])


def test_sudo_wrapped_binary_inside_allowlist_is_permitted(tmp_path):
    v = _sudo_validator(tmp_path)
    allowed_sudo = tmp_path / "sudo"
    allowed_sudo.write_text("")
    allowed_bin = tmp_path / "gstatus"
    allowed_bin.write_text("")
    assert v.check_exec([str(allowed_sudo), "-u", "root", str(allowed_bin)]) is None


def test_noop_validator_ignores_wrappers():
    osx = OSInterface()
    # No enforcement: unwrapping must not change passthrough behavior.
    assert osx._validator.check_exec(["sudo", "/usr/bin/anything"]) is None


# --------------------------------------------------------------------------- #
# shell=True: the shell is what launches, so it is what must be validated.
# Validating the first token of the command string would report on a program
# that never runs.
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(os.name == 'nt', reason='POSIX shell semantics')
def test_shell_true_validates_the_shell_not_the_command_token(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        # The command token is allowlisted; the shell is not.
        file_paths_allowlist=[str(tmp_path)],
    )
    allowed = tmp_path / "safe"
    allowed.write_text("")
    osx = OSInterface(TrustedProviderValidator(sec))
    with pytest.raises(PermissionError, match="/bin/sh"):
        osx.run(f"{allowed} && /usr/bin/evil", shell=True, capture_output=True)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX shell semantics')
def test_shell_true_permitted_when_shell_is_allowlisted(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        path_enforcement_mode='enforce',
        trusted_providers=["file"],
        file_paths_allowlist=["/bin", "/usr/bin"],
    )
    osx = OSInterface(TrustedProviderValidator(sec))
    result = osx.run("echo shell-ok", shell=True, capture_output=True, text=True)
    assert result.stdout.strip() == "shell-ok"


@pytest.mark.skipif(os.name == 'nt', reason='POSIX shell semantics')
def test_shell_exec_argv_shapes():
    from datadog_checks.base.utils.os_interface import _shell_exec_argv

    assert _shell_exec_argv("a && b") == ["/bin/sh", "-c", "a && b"]
    assert _shell_exec_argv(["a && b", "arg0"]) == ["/bin/sh", "-c", "a && b", "arg0"]


def test_shell_true_is_passthrough_under_noop_validator():
    # Parity: the no-op validator must not change shell=True behavior.
    osx = OSInterface()
    result = osx.run("echo parity", shell=True, capture_output=True, text=True)
    assert result.stdout.strip() == "parity"


def test_shell_false_still_validates_the_program():
    osx = OSInterface()
    assert osx._launched_argv(["ls", "-l"], {}) == ["ls", "-l"]
    assert osx._launched_argv(["ls", "-l"], {"shell": False}) == ["ls", "-l"]


# --------------------------------------------------------------------------- #
# Enforcement completeness: EVERY public method must consult the validator.
#
# This is the security invariant of the whole design. Without it, a method that
# forgets its validator hook, or a newly added one, silently becomes an
# unguarded bypass while every other test still passes. The registry below is
# asserted to cover the full public surface, so adding a method to OSInterface
# fails this test until it is exercised here.
# --------------------------------------------------------------------------- #
def _all_operations(osx, tmp_path):
    """Map every public OSInterface method name to a thunk that invokes it."""
    import sys

    src = tmp_path / "src.txt"
    src.write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    link = tmp_path / "link"
    link.symlink_to(src)
    noop_cmd = [sys.executable, "-c", "pass"]

    def _os_open():
        os.close(osx.os_open(str(src), os.O_RDONLY))

    def _scandir():
        with osx.scandir(str(tmp_path)):
            pass

    def _open():
        with osx.open(str(src)):
            pass

    def _popen():
        osx.popen(noop_cmd, stdout=subprocess.PIPE).communicate()

    return {
        "open": _open,
        "os_open": _os_open,
        "exists": lambda: osx.exists(str(src)),
        "isfile": lambda: osx.isfile(str(src)),
        "isdir": lambda: osx.isdir(str(sub)),
        "islink": lambda: osx.islink(str(link)),
        "getsize": lambda: osx.getsize(str(src)),
        "access": lambda: osx.access(str(src), os.R_OK),
        "stat": lambda: osx.stat(str(src)),
        "listdir": lambda: osx.listdir(str(tmp_path)),
        "glob": lambda: osx.glob(str(tmp_path / "*")),
        "scandir": _scandir,
        "walk": lambda: list(osx.walk(str(tmp_path))),
        "realpath": lambda: osx.realpath(str(src)),
        "resolve_path": lambda: osx.resolve_path(str(src)),
        "validate_path": lambda: osx.validate_path(str(src)),
        "which": lambda: osx.which("python3"),
        "copy": lambda: osx.copy(str(src), str(tmp_path / "dst.txt")),
        "run": lambda: osx.run(noop_cmd, capture_output=True),
        "popen": _popen,
        "get_subprocess_output": lambda: osx.get_subprocess_output(
            noop_cmd, mock.MagicMock(), raise_on_empty_output=False
        ),
    }


def _public_methods():
    return {name for name in dir(OSInterface) if not name.startswith("_") and callable(getattr(OSInterface, name))}


def test_operation_registry_covers_full_public_surface(tmp_path):
    # Guards the test below: a newly added public method must be registered here,
    # otherwise it would escape the enforcement check entirely.
    assert set(_all_operations(OSInterface(), tmp_path)) == _public_methods()


def test_every_public_method_consults_the_validator(tmp_path):
    v = RecordingValidator()
    osx = OSInterface(v)

    unguarded = []
    for name, operation in _all_operations(osx, tmp_path).items():
        before = len(v.path_calls) + len(v.exec_calls)
        operation()
        if len(v.path_calls) + len(v.exec_calls) == before:
            unguarded.append(name)

    assert not unguarded, f"methods missing a check_path/check_exec hook: {sorted(unguarded)}"


def test_every_path_method_can_be_denied(tmp_path):
    """A deny must propagate as PermissionError out of each path-consuming method."""
    src = tmp_path / "src.txt"
    src.write_text("x")
    target = str(src)
    v = RecordingValidator(deny_paths={target})
    osx = OSInterface(v)

    path_ops = {
        "open": lambda: osx.open(target),
        "os_open": lambda: osx.os_open(target, os.O_RDONLY),
        "exists": lambda: osx.exists(target),
        "isfile": lambda: osx.isfile(target),
        "isdir": lambda: osx.isdir(target),
        "islink": lambda: osx.islink(target),
        "getsize": lambda: osx.getsize(target),
        "access": lambda: osx.access(target, os.R_OK),
        "stat": lambda: osx.stat(target),
        "listdir": lambda: osx.listdir(target),
        "glob": lambda: osx.glob(target),
        "scandir": lambda: osx.scandir(target),
        "walk": lambda: osx.walk(target),
        "realpath": lambda: osx.realpath(target),
        "resolve_path": lambda: osx.resolve_path(target),
        "validate_path": lambda: osx.validate_path(target),
        "copy": lambda: osx.copy(target, str(tmp_path / "out.txt")),
    }
    for operation in path_ops.values():
        with pytest.raises(PermissionError):
            operation()


def test_every_exec_method_can_be_denied():
    v = RecordingValidator(deny_execs={"/usr/bin/evil"})
    osx = OSInterface(v)
    cmd = ["/usr/bin/evil", "--flag"]

    with pytest.raises(PermissionError):
        osx.run(cmd)
    with pytest.raises(PermissionError):
        osx.popen(cmd)
    with pytest.raises(PermissionError):
        osx.get_subprocess_output(cmd, mock.MagicMock())
    with pytest.raises(PermissionError):
        osx.which("/usr/bin/evil")


# --------------------------------------------------------------------------- #
# Remaining branch coverage
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("option", ["--login", "--shell"])
def test_sudo_long_shell_options_have_no_static_target(option):
    from datadog_checks.base.utils.os_interface import _exec_targets

    assert _exec_targets(["sudo", option]) == ["sudo"]


def test_shell_exec_argv_on_windows(monkeypatch):
    from datadog_checks.base.utils import os_interface as module

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    assert module._shell_exec_argv("dir") == [r"C:\Windows\System32\cmd.exe", "/c", "dir"]


# --------------------------------------------------------------------------- #
# Gap 1: point-of-use enforcement has its OWN mode, independent of the
# field-validation flag, plus a log-only dry run. Enabling field validation must
# NOT silently switch on enforcement at every migrated call site.
# --------------------------------------------------------------------------- #
def _sec(mode=None, allowlist=(), **kw):
    kwargs = {
        "check_name": "c",
        "provider": "untrusted",
        "ignore_untrusted_file_params": True,
        "trusted_providers": ["file"],
        "file_paths_allowlist": list(allowlist),
    }
    kwargs.update(kw)
    if mode is not None:
        kwargs["path_enforcement_mode"] = mode
    return SecurityConfig(**kwargs)


def test_enforcement_defaults_to_off_even_when_field_validation_is_on(tmp_path):
    # The kill switch: field validation enabled, point-of-use enforcement absent.
    sec = _sec(allowlist=[str(tmp_path / "nothing")])
    assert sec.path_enforcement_mode == 'off'
    osx = OSInterface(TrustedProviderValidator(sec))
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    assert osx.exists(str(denied)) is True  # allowed: enforcement off


def test_enforce_mode_denies(tmp_path):
    sec = _sec(mode='enforce', allowlist=[str(tmp_path / "nothing")])
    osx = OSInterface(TrustedProviderValidator(sec))
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    with pytest.raises(PermissionError):
        osx.exists(str(denied))


def test_log_mode_allows_but_reports(tmp_path):
    sec = _sec(mode='log', allowlist=[str(tmp_path / "nothing")])
    log = mock.MagicMock()
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    assert osx.exists(str(denied)) is True  # dry run: not blocked
    assert log.warning.called
    assert "would be denied" in log.warning.call_args[0][0]


def test_log_mode_reports_exec_violations(tmp_path):
    sec = _sec(mode='log', allowlist=[str(tmp_path)])
    log = mock.MagicMock()
    v = TrustedProviderValidator(sec, log=log)
    assert v.check_exec(["/usr/bin/evil"]) is None
    assert log.warning.called


def test_log_mode_is_silent_when_allowed(tmp_path):
    sec = _sec(mode='log', allowlist=[str(tmp_path)])
    log = mock.MagicMock()
    allowed = tmp_path / "ok.txt"
    allowed.write_text("x")
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    osx.exists(str(allowed))
    assert not log.warning.called


def test_unknown_enforcement_mode_fails_closed_to_off(tmp_path):
    # A typo in the Agent config must not silently enforce, nor crash the check.
    sec = _sec(mode='enfroce', allowlist=[str(tmp_path / "nothing")])
    log = mock.MagicMock()
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    assert osx.exists(str(denied)) is True
    assert log.warning.called  # misconfiguration is surfaced


def test_enforcement_mode_requires_field_validation_enabled(tmp_path):
    # is_enabled() is still the master switch; mode alone must not enforce.
    sec = _sec(mode='enforce', ignore_untrusted_file_params=False, allowlist=[])
    osx = OSInterface(TrustedProviderValidator(sec))
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    assert osx.exists(str(denied)) is True


def test_excluded_check_bypasses_enforcement(tmp_path):
    sec = _sec(mode='enforce', allowlist=[], excluded_checks=["c"])
    osx = OSInterface(TrustedProviderValidator(sec))
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    assert osx.exists(str(denied)) is True


# --------------------------------------------------------------------------- #
# Gap 3: a bare command name must be resolved the way the OS resolves it (via
# PATH) before the allowlist check. Otherwise `sudo`/`gunicorn`/`lsid` realpath
# against the CWD and every check that uses a bare name breaks under enforcement.
# --------------------------------------------------------------------------- #
def test_bare_command_name_resolved_via_path_and_allowed(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    tool = bindir / "mytool"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))

    sec = _sec(mode='enforce', allowlist=[str(bindir)])
    v = TrustedProviderValidator(sec)
    # Bare name resolves to <bindir>/mytool, which is allowlisted.
    assert v.check_exec(["mytool", "--flag"]) is None


def test_bare_command_name_resolved_via_path_and_denied(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    tool = bindir / "mytool"
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))

    other = tmp_path / "allowed_only"
    other.mkdir()
    sec = _sec(mode='enforce', allowlist=[str(other)])
    v = TrustedProviderValidator(sec)
    with pytest.raises(PermissionError):
        v.check_exec(["mytool"])


def test_unresolvable_bare_command_is_denied_not_crashed(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    sec = _sec(mode='enforce', allowlist=[str(tmp_path)])
    v = TrustedProviderValidator(sec)
    with pytest.raises(PermissionError):
        v.check_exec(["definitely-not-on-path"])


def test_path_arguments_are_not_path_resolved(tmp_path):
    # Only exec targets get PATH resolution; file paths must not.
    sec = _sec(mode='enforce', allowlist=[str(tmp_path)])
    v = TrustedProviderValidator(sec)
    with pytest.raises(PermissionError):
        v.check_path("relative_file.txt", "r")


def test_sudo_wrapped_bare_name_is_resolved(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("sudo", "mytool"):
        p = bindir / name
        p.write_text("#!/bin/sh\n")
        p.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))
    sec = _sec(mode='enforce', allowlist=[str(bindir)])
    v = TrustedProviderValidator(sec)
    assert v.check_exec(["sudo", "mytool"]) is None


# --------------------------------------------------------------------------- #
# AgentCheck wiring: the enforcement mode comes from its own Agent config key,
# and the validator logs through the check's logger.
# --------------------------------------------------------------------------- #
def test_agentcheck_reads_enforcement_mode_from_agent_config(datadog_agent):
    from datadog_checks.base import AgentCheck

    datadog_agent._config['integration_path_enforcement_mode'] = 'log'
    check = AgentCheck("c", {}, [{}])
    assert check.security_config.path_enforcement_mode == 'log'


def test_agentcheck_enforcement_mode_defaults_to_off(datadog_agent):
    from datadog_checks.base import AgentCheck

    check = AgentCheck("c", {}, [{}])
    assert check.security_config.path_enforcement_mode == 'off'


def test_agentcheck_validator_logs_through_check_logger(datadog_agent, tmp_path):
    from datadog_checks.base import AgentCheck

    datadog_agent._config['integration_path_enforcement_mode'] = 'log'
    datadog_agent._config['integration_ignore_untrusted_file_params'] = True
    datadog_agent._config['integration_file_paths_allowlist'] = [str(tmp_path / "nothing")]
    check = AgentCheck("c", {}, [{}])
    check.provider = 'untrusted'
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    with mock.patch.object(check, 'log') as log:
        # Rebuild the interface so it picks up the patched logger.
        check._AgentCheck__os_interface = None
        check._AgentCheck__security_config = None
        assert check.os_interface.exists(str(denied)) is True
        assert log.warning.called


# --------------------------------------------------------------------------- #
# Gap 8: glob. infiniband enumerates a config-derived path with glob.glob, which
# had no expression through the interface and was therefore unguarded.
# --------------------------------------------------------------------------- #
def test_glob_matches_stdlib(osx, tmp_path):
    import glob as glob_module

    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "c.log").write_text("")
    pattern = str(tmp_path / "*.txt")
    assert sorted(osx.glob(pattern)) == sorted(glob_module.glob(pattern))


def test_glob_recursive_matches_stdlib(osx, tmp_path):
    import glob as glob_module

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("")
    pattern = str(tmp_path / "**" / "*.txt")
    assert sorted(osx.glob(pattern, recursive=True)) == sorted(glob_module.glob(pattern, recursive=True))


def test_glob_no_match_returns_empty(osx, tmp_path):
    assert osx.glob(str(tmp_path / "*.nope")) == []


def test_glob_consults_the_validator(tmp_path):
    v = RecordingValidator()
    osx = OSInterface(v)
    osx.glob(str(tmp_path / "*"))
    assert v.path_calls, "glob must be validated like any other listing operation"


def test_glob_can_be_denied(tmp_path):
    pattern = str(tmp_path / "*")
    v = RecordingValidator(deny_paths={pattern})
    osx = OSInterface(v)
    with pytest.raises(PermissionError):
        osx.glob(pattern)


# --------------------------------------------------------------------------- #
# Shared TLS context builder: `tls_ca_cert`, `tls_cert` and `tls_private_key`
# are config-derived paths handed to ssl, which opens them itself. This is the
# path most integrations reach TLS through, so validating it covers many at once.
# --------------------------------------------------------------------------- #
def _tls_check(datadog_agent, tmp_path, mode, allowlist, instance):
    from datadog_checks.base import AgentCheck

    datadog_agent._config['integration_ignore_untrusted_file_params'] = True
    datadog_agent._config['integration_path_enforcement_mode'] = mode
    datadog_agent._config['integration_file_paths_allowlist'] = [str(p) for p in allowlist]
    datadog_agent._config['integration_trusted_providers'] = ['file']
    check = AgentCheck('c', {}, [instance])
    check.provider = 'untrusted'
    check._AgentCheck__security_config = None
    check._AgentCheck__os_interface = None
    return check


def test_tls_ca_cert_outside_allowlist_never_reaches_ssl(datadog_agent, tmp_path):
    check = _tls_check(datadog_agent, tmp_path, 'enforce', [tmp_path / 'allowed'], {'tls_ca_cert': '/tmp/evil/ca.pem'})
    with mock.patch('ssl.SSLContext.load_verify_locations') as load:
        with pytest.raises(PermissionError):
            check.get_tls_context()
    assert not load.called, "a disallowed CA cert must never reach ssl"


def test_tls_client_cert_outside_allowlist_never_reaches_ssl(datadog_agent, tmp_path):
    check = _tls_check(datadog_agent, tmp_path, 'enforce', [tmp_path / 'allowed'], {'tls_cert': '/tmp/evil/client.pem'})
    with mock.patch('ssl.SSLContext.load_cert_chain') as load:
        with pytest.raises(PermissionError):
            check.get_tls_context()
    assert not load.called, "a disallowed client cert must never reach ssl"


def test_tls_ca_cert_inside_allowlist_is_used(datadog_agent, tmp_path):
    allowed = tmp_path / 'allowed'
    allowed.mkdir()
    ca = allowed / 'ca.pem'
    ca.write_text('')
    check = _tls_check(datadog_agent, tmp_path, 'enforce', [allowed], {'tls_ca_cert': str(ca)})
    with mock.patch('ssl.SSLContext.load_verify_locations') as load:
        check.get_tls_context()
    assert load.called, "an allowlisted CA cert must still be used"


def test_tls_enforcement_off_by_default(datadog_agent, tmp_path):
    check = _tls_check(datadog_agent, tmp_path, 'off', [], {'tls_ca_cert': '/tmp/evil/ca.pem'})
    with mock.patch('ssl.SSLContext.load_verify_locations') as load:
        check.get_tls_context()
    assert load.called, "enforcement must default to off"


def test_tls_context_refresh_still_enforces(tmp_path):
    """refresh_tls_context rebuilds the context and must not drop the validator.

    Exercised directly on the wrapper: going through AgentCheck.get_tls_context
    would raise during construction and never reach the refresh path.
    """
    from datadog_checks.base.utils.tls import TlsContextWrapper

    allowed = tmp_path / 'allowed'
    allowed.mkdir()
    ca = allowed / 'ca.pem'
    ca.write_text('')
    sec = _sec(mode='enforce', allowlist=[str(allowed)])
    osx = OSInterface(TrustedProviderValidator(sec))

    with mock.patch('ssl.SSLContext.load_verify_locations') as load:
        wrapper = TlsContextWrapper({'tls_ca_cert': str(ca)}, os_interface=osx)
        assert load.called  # the allowlisted cert was accepted
        load.reset_mock()

        # Repoint at a disallowed path, then refresh: the rebuild must revalidate.
        wrapper.config['tls_ca_cert'] = '/tmp/evil/ca.pem'
        with pytest.raises(PermissionError):
            wrapper.refresh_tls_context()
        assert not load.called


# --------------------------------------------------------------------------- #
# validate_path: for library handoffs where the exact value the caller supplied
# must be preserved. resolve_path also rewrites relative paths to absolute ones,
# which changes what the library receives and so breaks parity.
# --------------------------------------------------------------------------- #
def test_validate_path_returns_the_input_unchanged(osx):
    assert osx.validate_path('foo') == 'foo'
    assert osx.validate_path('~/rel/../x') == '~/rel/../x'
    assert osx.validate_path('/abs/path') == '/abs/path'


def test_validate_path_consults_the_validator(tmp_path):
    v = RecordingValidator()
    osx = OSInterface(v)
    osx.validate_path(str(tmp_path / 'x'))
    assert v.path_calls


def test_validate_path_can_be_denied(tmp_path):
    target = str(tmp_path / 'x')
    osx = OSInterface(RecordingValidator(deny_paths={target}))
    with pytest.raises(PermissionError):
        osx.validate_path(target)


def test_resolve_path_still_resolves(osx, tmp_path):
    # The two are deliberately different: resolve_path normalizes, validate_path
    # does not. Callers that need the resolved form keep using resolve_path.
    p = tmp_path / 'x'
    assert osx.resolve_path(str(p)) == os.path.realpath(str(p))


def test_unknown_mode_warns_once_not_per_operation(tmp_path):
    """A misconfigured mode must not log once per file operation.

    Checks run on a schedule and perform many operations per run, so warning
    every time would flood the Agent log with a single configuration mistake.
    """
    sec = _sec(mode='enfroce', allowlist=[str(tmp_path)])
    log = mock.MagicMock()
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    for _ in range(25):
        osx.exists(str(tmp_path / 'x'))
    assert log.warning.call_count == 1


def test_log_mode_reports_each_violation_once(tmp_path):
    """Dry-run reporting must not repeat per operation or per check run.

    The diagnostic value is knowing which paths would be denied; repeating the
    same line on every scheduled run would drown the log.
    """
    sec = _sec(mode='log', allowlist=[str(tmp_path / 'allowed')])
    log = mock.MagicMock()
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    for _ in range(10):
        osx.exists('/tmp/evil/a.txt')
    assert log.warning.call_count == 1


def test_log_mode_reports_distinct_violations_separately(tmp_path):
    sec = _sec(mode='log', allowlist=[str(tmp_path / 'allowed')])
    log = mock.MagicMock()
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    osx.exists('/tmp/evil/a.txt')
    osx.exists('/tmp/evil/b.txt')
    assert log.warning.call_count == 2


def test_violation_dedup_memory_is_bounded(tmp_path):
    """The dedup set must not grow without bound.

    A validator lives as long as its check, so a check that touches many
    distinct disallowed paths would otherwise leak one entry per path for the
    lifetime of the Agent.
    """
    from datadog_checks.base.utils.os_interface import MAX_REPORTED_VIOLATIONS

    sec = _sec(mode='log', allowlist=[str(tmp_path / 'allowed')])
    log = mock.MagicMock()
    validator = TrustedProviderValidator(sec, log=log)
    osx = OSInterface(validator)
    for i in range(MAX_REPORTED_VIOLATIONS * 3):
        osx.exists(f'/tmp/evil/{i}.txt')
    assert len(validator._reported_violations) <= MAX_REPORTED_VIOLATIONS


def test_violation_suppression_is_announced(tmp_path):
    from datadog_checks.base.utils.os_interface import MAX_REPORTED_VIOLATIONS

    sec = _sec(mode='log', allowlist=[str(tmp_path / 'allowed')])
    log = mock.MagicMock()
    osx = OSInterface(TrustedProviderValidator(sec, log=log))
    for i in range(MAX_REPORTED_VIOLATIONS + 5):
        osx.exists(f'/tmp/evil/{i}.txt')
    messages = [str(c) for c in log.warning.call_args_list]
    assert any('suppress' in m for m in messages), "hitting the cap must be visible in the log"
