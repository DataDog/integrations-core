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
from datadog_checks.base.utils.os_wrapper import (
    NoOpValidator,
    OSWrapper,
    TrustedProviderValidator,
    unchecked_os,
)


@pytest.fixture
def wrapper():
    return OSWrapper()


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
def test_open_default_mode_is_read(wrapper, tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello")
    with wrapper.open(str(p)) as f:
        assert f.read() == "hello"
        assert f.mode == "r"


def test_open_read_write_roundtrip(wrapper, tmp_path):
    p = tmp_path / "f.txt"
    with wrapper.open(str(p), "w") as f:
        f.write("data")
    with wrapper.open(str(p)) as f:
        assert f.read() == "data"


def test_open_created_file_permission_bits_match_builtin(wrapper, tmp_path):
    # Regression guard: the earlier prototype wired a custom opener that called
    # os.open() without a mode, producing 0o777-derived bits instead of
    # builtin open()'s 0o666-derived bits. Created files must match builtin open.
    ref = tmp_path / "ref.txt"
    with open(str(ref), "w") as f:
        f.write("x")
    got = tmp_path / "got.txt"
    with wrapper.open(str(got), "w") as f:
        f.write("x")
    assert stat.S_IMODE(os.stat(got).st_mode) == stat.S_IMODE(os.stat(ref).st_mode)


def test_open_binary_mode(wrapper, tmp_path):
    p = tmp_path / "b.bin"
    with wrapper.open(str(p), "wb") as f:
        f.write(b"\x00\x01")
    with wrapper.open(str(p), "rb") as f:
        assert f.read() == b"\x00\x01"


def test_open_missing_file_raises_same_exception(wrapper, tmp_path):
    missing = str(tmp_path / "nope.txt")
    with pytest.raises(FileNotFoundError):
        wrapper.open(missing)


def test_open_encoding_passthrough(wrapper, tmp_path):
    p = tmp_path / "u.txt"
    with wrapper.open(str(p), "w", encoding="utf-8") as f:
        f.write("café")
    with wrapper.open(str(p), encoding="utf-8") as f:
        assert f.read() == "café"


def test_os_open_raw_fd_roundtrip(wrapper, tmp_path):
    p = tmp_path / "raw.txt"
    fd = wrapper.os_open(str(p), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        os.write(fd, b"z")
    finally:
        os.close(fd)
    if os.name != 'nt':
        # Windows does not implement POSIX mode bits; only the read-only flag is
        # honored, so the value would not round-trip.
        assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert p.read_bytes() == b"z"


# --------------------------------------------------------------------------- #
# predicates
# --------------------------------------------------------------------------- #
def test_predicates_match_stdlib(wrapper, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("123")
    d = tmp_path / "sub"
    d.mkdir()
    missing = tmp_path / "missing"

    for target in (f, d, missing):
        s = str(target)
        assert wrapper.exists(s) == os.path.exists(s)
        assert wrapper.isfile(s) == os.path.isfile(s)
        assert wrapper.isdir(s) == os.path.isdir(s)
        assert wrapper.islink(s) == os.path.islink(s)

    assert wrapper.getsize(str(f)) == os.path.getsize(str(f))
    assert wrapper.access(str(f), os.R_OK) == os.access(str(f), os.R_OK)


def test_stat_matches_stdlib(wrapper, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("123")
    assert wrapper.stat(str(f)).st_size == os.stat(str(f)).st_size


def test_getsize_missing_raises(wrapper, tmp_path):
    with pytest.raises(OSError):
        wrapper.getsize(str(tmp_path / "missing"))


# --------------------------------------------------------------------------- #
# listing
# --------------------------------------------------------------------------- #
def test_listdir_matches_stdlib(wrapper, tmp_path):
    (tmp_path / "a").write_text("")
    (tmp_path / "b").write_text("")
    assert sorted(wrapper.listdir(str(tmp_path))) == sorted(os.listdir(str(tmp_path)))


def test_scandir_matches_stdlib(wrapper, tmp_path):
    (tmp_path / "a").write_text("")
    (tmp_path / "b").write_text("")
    with wrapper.scandir(str(tmp_path)) as it:
        names = sorted(e.name for e in it)
    assert names == sorted(os.listdir(str(tmp_path)))


def test_walk_matches_stdlib_and_is_lazy(wrapper, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f").write_text("")
    got = {(r, tuple(sorted(d)), tuple(sorted(f))) for r, d, f in wrapper.walk(str(tmp_path))}
    ref = {(r, tuple(sorted(d)), tuple(sorted(f))) for r, d, f in os.walk(str(tmp_path))}
    assert got == ref


def test_walk_on_missing_path_yields_nothing_like_stdlib(wrapper, tmp_path):
    missing = str(tmp_path / "missing")
    assert list(wrapper.walk(missing)) == list(os.walk(missing))


# --------------------------------------------------------------------------- #
# path resolution / lookup
# --------------------------------------------------------------------------- #
def test_realpath_matches_stdlib(wrapper, tmp_path):
    p = str(tmp_path / "x")
    assert wrapper.realpath(p) == os.path.realpath(p)
    assert wrapper.resolve_path(p) == os.path.realpath(p)


def test_which_matches_stdlib(wrapper):
    import shutil

    assert wrapper.which("sh") == shutil.which("sh")
    assert wrapper.which("this-binary-does-not-exist-xyz") is None


def test_copy_matches_stdlib(wrapper, tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("payload")
    dst = tmp_path / "dst.txt"
    wrapper.copy(str(src), str(dst))
    assert dst.read_text() == "payload"


# --------------------------------------------------------------------------- #
# subprocess family
# --------------------------------------------------------------------------- #
def test_run_passthrough(wrapper):
    result = wrapper.run(["echo", "hi"], capture_output=True, text=True)
    ref = subprocess.run(["echo", "hi"], capture_output=True, text=True)
    assert result.stdout == ref.stdout == "hi\n"
    assert result.returncode == 0


def test_popen_passthrough(wrapper):
    proc = wrapper.popen(["echo", "hi"], stdout=subprocess.PIPE, text=True)
    out, _ = proc.communicate()
    assert out == "hi\n"
    assert proc.returncode == 0


def test_get_subprocess_output_passthrough(wrapper):
    import logging

    log = logging.getLogger("test")
    out, err, code = wrapper.get_subprocess_output(["echo", "hi"], log)
    assert out.strip() == "hi"
    assert code == 0


# --------------------------------------------------------------------------- #
# validator enforcement
# --------------------------------------------------------------------------- #
def test_validator_invoked_on_path_ops(tmp_path):
    v = RecordingValidator()
    wrapper = OSWrapper(v)
    f = tmp_path / "a.txt"
    f.write_text("x")
    wrapper.exists(str(f))
    wrapper.isfile(str(f))
    with wrapper.open(str(f)):
        pass
    modes = {mode for _, mode in v.path_calls}
    assert v.path_calls  # validator was consulted
    assert "r" in modes


def test_validator_can_deny_path(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    v = RecordingValidator(deny_paths={str(f)})
    wrapper = OSWrapper(v)
    with pytest.raises(PermissionError):
        wrapper.open(str(f))
    # denial happens before the real call: file is never opened
    assert v.path_calls == [(str(f), "r")]


def test_open_write_mode_reported_to_validator(tmp_path):
    v = RecordingValidator()
    wrapper = OSWrapper(v)
    with wrapper.open(str(tmp_path / "w.txt"), "w"):
        pass
    assert (str(tmp_path / "w.txt"), "w") in v.path_calls


def test_validator_invoked_on_exec(wrapper=None):
    v = RecordingValidator()
    wrapper = OSWrapper(v)
    wrapper.run(["echo", "hi"], capture_output=True)
    assert v.exec_calls == [["echo", "hi"]]


def test_validator_can_deny_exec():
    v = RecordingValidator(deny_execs={"echo"})
    wrapper = OSWrapper(v)
    with pytest.raises(PermissionError):
        wrapper.run(["echo", "hi"], capture_output=True)
    assert v.exec_calls == [["echo", "hi"]]


def test_exec_string_command_validated_as_argv0():
    v = RecordingValidator()
    wrapper = OSWrapper(v)
    # get_subprocess_output accepts a whitespace-split string command
    import logging

    wrapper.get_subprocess_output("echo hi", logging.getLogger("t"))
    assert v.exec_calls[0][0] == "echo"


# --------------------------------------------------------------------------- #
# module-level default singleton
# --------------------------------------------------------------------------- #
def test_module_singleton_is_noop(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text("ok")
    assert unchecked_os.exists(str(p)) is True
    with unchecked_os.open(str(p)) as f:
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
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    f = tmp_path / "a.txt"
    f.write_text("x")
    with wrapper.open(str(f)) as fh:
        assert fh.read() == "x"


def test_trusted_provider_trusted_provider_passes(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="file",
        ignore_untrusted_file_params=True,
        trusted_providers=["file"],
        file_paths_allowlist=[],
    )
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    f = tmp_path / "a.txt"
    f.write_text("x")
    with wrapper.open(str(f)):
        pass  # trusted provider: allowed despite empty allowlist


def test_trusted_provider_untrusted_outside_allowlist_denied(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        trusted_providers=["file"],
        file_paths_allowlist=[str(tmp_path / "allowed")],
    )
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    with pytest.raises(PermissionError):
        wrapper.open(str(f))


def test_trusted_provider_untrusted_inside_allowlist_allowed(tmp_path):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    f = allowed_dir / "a.txt"
    f.write_text("x")
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        trusted_providers=["file"],
        file_paths_allowlist=[str(allowed_dir)],
    )
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    with wrapper.open(str(f)) as fh:
        assert fh.read() == "x"


def test_trusted_provider_excluded_check_passes(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        excluded_checks=["c"],
        file_paths_allowlist=[],
    )
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    with wrapper.open(str(f)):
        pass


def test_trusted_provider_gates_exec_by_binary_path(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        trusted_providers=["file"],
        file_paths_allowlist=[str(tmp_path / "allowed_bin")],
    )
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    with pytest.raises(PermissionError):
        wrapper.run(["/usr/bin/evil", "--flag"], capture_output=True)


# --------------------------------------------------------------------------- #
# AgentCheck integration
# --------------------------------------------------------------------------- #
def test_agentcheck_exposes_bound_interface(tmp_path):
    from datadog_checks.base import AgentCheck

    check = AgentCheck("c", {}, [{}])
    assert isinstance(check.os, OSWrapper)
    # cached
    assert check.os is check.os
    # default config disables enforcement -> passthrough
    p = tmp_path / "a.txt"
    p.write_text("ok")
    assert check.os.exists(str(p)) is True


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
    from datadog_checks.base.utils.os_wrapper import _exec_targets

    assert _exec_targets(argv) == expected


def _sudo_validator(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
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
    wrapper = OSWrapper()
    # No enforcement: unwrapping must not change passthrough behavior.
    assert wrapper._validator.check_exec(["sudo", "/usr/bin/anything"]) is None


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
        trusted_providers=["file"],
        # The command token is allowlisted; the shell is not.
        file_paths_allowlist=[str(tmp_path)],
    )
    allowed = tmp_path / "safe"
    allowed.write_text("")
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    with pytest.raises(PermissionError, match="/bin/sh"):
        wrapper.run(f"{allowed} && /usr/bin/evil", shell=True, capture_output=True)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX shell semantics')
def test_shell_true_permitted_when_shell_is_allowlisted(tmp_path):
    sec = SecurityConfig(
        check_name="c",
        provider="untrusted",
        ignore_untrusted_file_params=True,
        trusted_providers=["file"],
        file_paths_allowlist=["/bin", "/usr/bin"],
    )
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    result = wrapper.run("echo shell-ok", shell=True, capture_output=True, text=True)
    assert result.stdout.strip() == "shell-ok"


@pytest.mark.skipif(os.name == 'nt', reason='POSIX shell semantics')
def test_shell_exec_argv_shapes():
    from datadog_checks.base.utils.os_wrapper import _shell_exec_argv

    assert _shell_exec_argv("a && b") == ["/bin/sh", "-c", "a && b"]
    assert _shell_exec_argv(["a && b", "arg0"]) == ["/bin/sh", "-c", "a && b", "arg0"]


def test_shell_true_is_passthrough_under_noop_validator():
    # Parity: the no-op validator must not change shell=True behavior.
    wrapper = OSWrapper()
    result = wrapper.run("echo parity", shell=True, capture_output=True, text=True)
    assert result.stdout.strip() == "parity"


def test_shell_false_still_validates_the_program():
    wrapper = OSWrapper()
    assert wrapper._launched_argv(["ls", "-l"], {}) == ["ls", "-l"]
    assert wrapper._launched_argv(["ls", "-l"], {"shell": False}) == ["ls", "-l"]


# --------------------------------------------------------------------------- #
# Enforcement completeness: EVERY public method must consult the validator.
#
# This is the security invariant of the whole design. Without it, a method that
# forgets its validator hook, or a newly added one, silently becomes an
# unguarded bypass while every other test still passes. The registry below is
# asserted to cover the full public surface, so adding a method to OSWrapper
# fails this test until it is exercised here.
# --------------------------------------------------------------------------- #
def _all_operations(wrapper, tmp_path):
    """Map every public OSWrapper method name to a thunk that invokes it."""
    import sys

    src = tmp_path / "src.txt"
    src.write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    link = tmp_path / "link"
    link.symlink_to(src)
    noop_cmd = [sys.executable, "-c", "pass"]

    def _os_open():
        os.close(wrapper.os_open(str(src), os.O_RDONLY))

    def _scandir():
        with wrapper.scandir(str(tmp_path)):
            pass

    def _open():
        with wrapper.open(str(src)):
            pass

    def _popen():
        wrapper.popen(noop_cmd, stdout=subprocess.PIPE).communicate()

    return {
        "open": _open,
        "os_open": _os_open,
        "exists": lambda: wrapper.exists(str(src)),
        "isfile": lambda: wrapper.isfile(str(src)),
        "isdir": lambda: wrapper.isdir(str(sub)),
        "islink": lambda: wrapper.islink(str(link)),
        "getsize": lambda: wrapper.getsize(str(src)),
        "access": lambda: wrapper.access(str(src), os.R_OK),
        "stat": lambda: wrapper.stat(str(src)),
        "listdir": lambda: wrapper.listdir(str(tmp_path)),
        "glob": lambda: wrapper.glob(str(tmp_path / "*")),
        "scandir": _scandir,
        "walk": lambda: list(wrapper.walk(str(tmp_path))),
        "realpath": lambda: wrapper.realpath(str(src)),
        "resolve_path": lambda: wrapper.resolve_path(str(src)),
        "validate_path": lambda: wrapper.validate_path(str(src)),
        "which": lambda: wrapper.which("python3"),
        "copy": lambda: wrapper.copy(str(src), str(tmp_path / "dst.txt")),
        "run": lambda: wrapper.run(noop_cmd, capture_output=True),
        "popen": _popen,
        "get_subprocess_output": lambda: wrapper.get_subprocess_output(
            noop_cmd, mock.MagicMock(), raise_on_empty_output=False
        ),
    }


def _public_methods():
    return {name for name in dir(OSWrapper) if not name.startswith("_") and callable(getattr(OSWrapper, name))}


def test_operation_registry_covers_full_public_surface(tmp_path):
    # Guards the test below: a newly added public method must be registered here,
    # otherwise it would escape the enforcement check entirely.
    assert set(_all_operations(OSWrapper(), tmp_path)) == _public_methods()


def test_every_public_method_consults_the_validator(tmp_path):
    v = RecordingValidator()
    wrapper = OSWrapper(v)

    unguarded = []
    for name, operation in _all_operations(wrapper, tmp_path).items():
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
    wrapper = OSWrapper(v)

    path_ops = {
        "open": lambda: wrapper.open(target),
        "os_open": lambda: wrapper.os_open(target, os.O_RDONLY),
        "exists": lambda: wrapper.exists(target),
        "isfile": lambda: wrapper.isfile(target),
        "isdir": lambda: wrapper.isdir(target),
        "islink": lambda: wrapper.islink(target),
        "getsize": lambda: wrapper.getsize(target),
        "access": lambda: wrapper.access(target, os.R_OK),
        "stat": lambda: wrapper.stat(target),
        "listdir": lambda: wrapper.listdir(target),
        "glob": lambda: wrapper.glob(target),
        "scandir": lambda: wrapper.scandir(target),
        "walk": lambda: wrapper.walk(target),
        "realpath": lambda: wrapper.realpath(target),
        "resolve_path": lambda: wrapper.resolve_path(target),
        "validate_path": lambda: wrapper.validate_path(target),
        "copy": lambda: wrapper.copy(target, str(tmp_path / "out.txt")),
    }
    for operation in path_ops.values():
        with pytest.raises(PermissionError):
            operation()


def test_every_exec_method_can_be_denied():
    v = RecordingValidator(deny_execs={"/usr/bin/evil"})
    wrapper = OSWrapper(v)
    cmd = ["/usr/bin/evil", "--flag"]

    with pytest.raises(PermissionError):
        wrapper.run(cmd)
    with pytest.raises(PermissionError):
        wrapper.popen(cmd)
    with pytest.raises(PermissionError):
        wrapper.get_subprocess_output(cmd, mock.MagicMock())
    with pytest.raises(PermissionError):
        wrapper.which("/usr/bin/evil")


# --------------------------------------------------------------------------- #
# Remaining branch coverage
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("option", ["--login", "--shell"])
def test_sudo_long_shell_options_have_no_static_target(option):
    from datadog_checks.base.utils.os_wrapper import _exec_targets

    assert _exec_targets(["sudo", option]) == ["sudo"]


def test_shell_exec_argv_on_windows(monkeypatch):
    from datadog_checks.base.utils import os_wrapper as module

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
    assert module._shell_exec_argv("dir") == [r"C:\Windows\System32\cmd.exe", "/c", "dir"]


# --------------------------------------------------------------------------- #
# Gap 1: point-of-use enforcement has its OWN mode, independent of the
# field-validation flag, plus a log-only dry run. Enabling field validation must
# NOT silently switch on enforcement at every migrated call site.
# --------------------------------------------------------------------------- #
def _sec(allowlist=(), **kw):
    kwargs = {
        "check_name": "c",
        "provider": "untrusted",
        "ignore_untrusted_file_params": True,
        "trusted_providers": ["file"],
        "file_paths_allowlist": list(allowlist),
    }
    kwargs.update(kw)
    return SecurityConfig(**kwargs)


def test_nothing_is_gated_while_field_validation_is_disabled(tmp_path):
    """The shipped default: `ignore_untrusted_file_params` off means no gating.

    Covers exec as well as paths, since a single flag now governs both and this
    is the state every migrated call site runs in until an operator opts in.
    """
    sec = _sec(ignore_untrusted_file_params=False, allowlist=[])
    validator = TrustedProviderValidator(sec)
    wrapper = OSWrapper(validator)
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    assert wrapper.exists(str(denied)) is True
    assert validator.check_exec(['/usr/bin/evil', '--flag']) is None
    assert validator.check_exec(['sudo', '/usr/bin/evil']) is None


def test_excluded_check_bypasses_enforcement(tmp_path):
    sec = _sec(allowlist=[], excluded_checks=["c"])
    wrapper = OSWrapper(TrustedProviderValidator(sec))
    denied = tmp_path / "outside.txt"
    denied.write_text("x")
    assert wrapper.exists(str(denied)) is True


# --------------------------------------------------------------------------- #
# Gap 3: a bare command name must be resolved the way the OS resolves it (via
# PATH) before the allowlist check. Otherwise `sudo`/`gunicorn`/`lsid` realpath
# against the CWD and every check that uses a bare name breaks under enforcement.
# --------------------------------------------------------------------------- #
def _make_tool(bindir, name):
    """Create an executable that `shutil.which` can find on this platform."""
    # Windows resolves bare names through PATHEXT, so a suffix-less file is invisible.
    tool = bindir / (f"{name}.bat" if os.name == 'nt' else name)
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    return tool


def test_bare_command_name_resolved_via_path_and_allowed(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _make_tool(bindir, "mytool")
    monkeypatch.setenv("PATH", str(bindir))

    sec = _sec(allowlist=[str(bindir)])
    v = TrustedProviderValidator(sec)
    # Bare name resolves under <bindir>, which is allowlisted.
    assert v.check_exec(["mytool", "--flag"]) is None


def test_bare_command_name_resolved_via_path_and_denied(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _make_tool(bindir, "mytool")
    monkeypatch.setenv("PATH", str(bindir))

    other = tmp_path / "allowed_only"
    other.mkdir()
    sec = _sec(allowlist=[str(other)])
    v = TrustedProviderValidator(sec)
    with pytest.raises(PermissionError):
        v.check_exec(["mytool"])


def test_unresolvable_bare_command_is_denied_not_crashed(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    sec = _sec(allowlist=[str(tmp_path)])
    v = TrustedProviderValidator(sec)
    with pytest.raises(PermissionError):
        v.check_exec(["definitely-not-on-path"])


def test_path_arguments_are_not_path_resolved(tmp_path):
    # Only exec targets get PATH resolution; file paths must not.
    sec = _sec(allowlist=[str(tmp_path)])
    v = TrustedProviderValidator(sec)
    with pytest.raises(PermissionError):
        v.check_path("relative_file.txt", "r")


@pytest.mark.skipif(os.name == 'nt', reason='sudo is a POSIX concept')
def test_sudo_wrapped_bare_name_is_resolved(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("sudo", "mytool"):
        _make_tool(bindir, name)
    monkeypatch.setenv("PATH", str(bindir))
    sec = _sec(allowlist=[str(bindir)])
    v = TrustedProviderValidator(sec)
    assert v.check_exec(["sudo", "mytool"]) is None


# --------------------------------------------------------------------------- #
# Gap 8: glob. infiniband enumerates a config-derived path with glob.glob, which
# had no expression through the interface and was therefore unguarded.
# --------------------------------------------------------------------------- #
def test_glob_matches_stdlib(wrapper, tmp_path):
    import glob as glob_module

    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "c.log").write_text("")
    pattern = str(tmp_path / "*.txt")
    assert sorted(wrapper.glob(pattern)) == sorted(glob_module.glob(pattern))


def test_glob_recursive_matches_stdlib(wrapper, tmp_path):
    import glob as glob_module

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.txt").write_text("")
    pattern = str(tmp_path / "**" / "*.txt")
    assert sorted(wrapper.glob(pattern, recursive=True)) == sorted(glob_module.glob(pattern, recursive=True))


def test_glob_no_match_returns_empty(wrapper, tmp_path):
    assert wrapper.glob(str(tmp_path / "*.nope")) == []


def test_glob_consults_the_validator(tmp_path):
    v = RecordingValidator()
    wrapper = OSWrapper(v)
    wrapper.glob(str(tmp_path / "*"))
    assert v.path_calls, "glob must be validated like any other listing operation"


def test_glob_can_be_denied(tmp_path):
    pattern = str(tmp_path / "*")
    v = RecordingValidator(deny_paths={pattern})
    wrapper = OSWrapper(v)
    with pytest.raises(PermissionError):
        wrapper.glob(pattern)


# --------------------------------------------------------------------------- #
# validate_path: for library handoffs where the exact value the caller supplied
# must be preserved. resolve_path also rewrites relative paths to absolute ones,
# which changes what the library receives and so breaks parity.
# --------------------------------------------------------------------------- #
def test_validate_path_returns_the_input_unchanged(wrapper):
    assert wrapper.validate_path('foo') == 'foo'
    assert wrapper.validate_path('~/rel/../x') == '~/rel/../x'
    assert wrapper.validate_path('/abs/path') == '/abs/path'


def test_validate_path_consults_the_validator(tmp_path):
    v = RecordingValidator()
    wrapper = OSWrapper(v)
    wrapper.validate_path(str(tmp_path / 'x'))
    assert v.path_calls


def test_validate_path_can_be_denied(tmp_path):
    target = str(tmp_path / 'x')
    wrapper = OSWrapper(RecordingValidator(deny_paths={target}))
    with pytest.raises(PermissionError):
        wrapper.validate_path(target)


def test_resolve_path_still_resolves(wrapper, tmp_path):
    # The two are deliberately different: resolve_path normalizes, validate_path
    # does not. Callers that need the resolved form keep using resolve_path.
    p = tmp_path / 'x'
    assert wrapper.resolve_path(str(p)) == os.path.realpath(str(p))


def test_tls_ca_cert_directory_probe_goes_through_unchecked_os(tmp_path):
    """The one direct filesystem call in the TLS builder is mediated.

    Everything else it does with a certificate path is handed to ssl, which
    opens the file itself and cannot be intercepted.
    """
    from datadog_checks.base.utils import tls

    capath = tmp_path / "certs"
    capath.mkdir()
    with mock.patch.object(tls.unchecked_os, 'isdir', wraps=tls.unchecked_os.isdir) as isdir:
        with mock.patch('ssl.SSLContext.load_verify_locations'):
            tls.create_ssl_context({'tls_verify': True, 'tls_ca_cert': str(capath)})
    isdir.assert_called_once_with(str(capath))
