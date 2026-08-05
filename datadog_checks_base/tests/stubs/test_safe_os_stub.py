# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
from unittest import mock

import pytest

from datadog_checks.base.stubs.safe_os import METHOD_NAMES, MockSafeOS

pytestmark = pytest.mark.unit


def test_methods_are_mocks():
    fake = MockSafeOS()
    for name in METHOD_NAMES:
        assert isinstance(getattr(fake, name), mock.MagicMock)

    # Unconfigured subprocess methods stay bare MagicMocks: callable and recording.
    fake.which("ls")
    fake.which.assert_called_with("ls")


def test_add_file_predicates_and_read():
    fake = MockSafeOS()
    fake.add_file("/etc/app/conf.yaml", "key: value")

    assert fake.exists("/etc/app/conf.yaml") is True
    assert fake.isfile("/etc/app/conf.yaml") is True
    assert fake.isdir("/etc/app/conf.yaml") is False
    assert fake.getsize("/etc/app/conf.yaml") == len("key: value")

    with fake.open("/etc/app/conf.yaml") as f:
        assert f.read() == "key: value"


def test_add_file_registers_parent_dirs():
    fake = MockSafeOS()
    fake.add_file("/a/b/c.txt", "x")

    assert fake.isdir("/a") is True
    assert fake.isdir("/a/b") is True
    assert fake.exists("/a/b") is True
    assert fake.listdir("/a/b") == ["c.txt"]


def test_trailing_slash_normalized():
    fake = MockSafeOS()
    fake.add_dir("/data/")
    assert fake.isdir("/data") is True
    assert fake.isdir("/data/") is True


def test_open_read_missing_file_raises():
    fake = MockSafeOS()
    with pytest.raises(FileNotFoundError):
        fake.open("/nope")


def test_open_binary_read():
    fake = MockSafeOS()
    fake.add_file("/blob", b"\x00\x01\x02")
    with fake.open("/blob", "rb") as f:
        assert f.read() == b"\x00\x01\x02"


def test_open_write_captures_content():
    fake = MockSafeOS()
    with fake.open("/out.txt", "w") as f:
        f.write("hello")
    assert fake.get_file("/out.txt") == "hello"


def test_open_append_preserves_existing():
    fake = MockSafeOS()
    fake.add_file("/log", "line1\n")
    with fake.open("/log", "a") as f:
        f.write("line2\n")
    assert fake.get_file("/log") == "line1\nline2\n"


def test_open_is_line_iterable():
    fake = MockSafeOS()
    fake.add_file("/status", "NSpid:\t42 7\nName:\tx\n")
    with fake.open("/status") as f:
        lines = list(f)
    assert lines[0].startswith("NSpid:")


def test_listdir_lists_files_and_dirs():
    fake = MockSafeOS()
    fake.add_file("/base/f1", "")
    fake.add_dir("/base/sub")
    assert fake.listdir("/base") == ["f1", "sub"]


def test_listdir_missing_dir_raises():
    fake = MockSafeOS()
    with pytest.raises(FileNotFoundError):
        fake.listdir("/missing")


def test_scandir_is_context_manager_with_entries():
    fake = MockSafeOS()
    fake.add_file("/proc/42/status", "")
    fake.add_dir("/proc/42")

    with fake.scandir("/proc") as entries:
        names = {(e.name, e.is_dir()) for e in entries}
    assert ("42", True) in names


def test_walk_traverses_tree():
    fake = MockSafeOS()
    fake.add_file("/root/a.txt", "")
    fake.add_file("/root/sub/b.txt", "")

    walked = {dirpath: (sorted(dirs), sorted(files)) for dirpath, dirs, files in fake.walk("/root")}
    assert walked["/root"] == (["sub"], ["a.txt"])
    assert walked["/root/sub"] == ([], ["b.txt"])


def test_set_command_output_get_subprocess_output():
    fake = MockSafeOS()
    fake.set_command_output("netstat -i", stdout="iface data", returncode=0)

    out, err, code = fake.get_subprocess_output("netstat -i", None)
    assert (out, err, code) == ("iface data", "", 0)


def test_set_command_output_matches_list_command():
    fake = MockSafeOS()
    fake.set_command_output(["ps", "aux"], stdout="procs")
    out, _, _ = fake.get_subprocess_output(["ps", "aux"], None)
    assert out == "procs"


def test_set_command_output_run_returns_completed_process():
    fake = MockSafeOS()
    fake.set_command_output("lparstat -m", stdout="mem", returncode=0)

    proc = fake.run(["lparstat", "-m"], text=True)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert proc.returncode == 0
    assert proc.stdout == "mem"


def test_run_bytes_when_not_text():
    fake = MockSafeOS()
    fake.set_command_output("lparstat -m", stdout="mem")
    proc = fake.run(["lparstat", "-m"])
    assert proc.stdout == b"mem"


def test_direct_mock_configuration_still_works():
    # The layer must not get in the way of raw mock usage.
    fake = MockSafeOS()
    fake.get_subprocess_output.return_value = ("x", "", 0)
    assert fake.get_subprocess_output("anything", None) == ("x", "", 0)

    fake.popen.side_effect = [mock_proc := object(), object()]
    assert fake.popen(["a"]) is mock_proc
    fake.popen.assert_called()


def test_method_names_covers_the_full_interface_surface():
    """Guard against drift between the real interface and the stub.

    A method added to SafeOS but missing here is not redirected by the
    `mock_safe_os` fixture, so a test using the fixture would silently
    reach the real filesystem instead of the fake.
    """
    from datadog_checks.base.utils.safe_os import SafeOS

    real = {name for name in dir(SafeOS) if not name.startswith("_") and callable(getattr(SafeOS, name))}
    assert set(METHOD_NAMES) == real


def test_glob_is_backed_by_the_in_memory_filesystem():
    fake = MockSafeOS()
    fake.add_files({"/etc/dd/a.conf": "", "/etc/dd/b.conf": "", "/etc/dd/c.txt": ""})
    assert sorted(fake.glob("/etc/dd/*.conf")) == ["/etc/dd/a.conf", "/etc/dd/b.conf"]


def test_glob_returns_empty_when_nothing_matches():
    fake = MockSafeOS()
    fake.add_file("/etc/dd/a.conf")
    assert fake.glob("/etc/dd/*.nope") == []


def test_walk_yields_the_registered_paths_verbatim():
    """Traversal must not re-join child paths.

    Re-joining with os.path.join emits a backslash on Windows while the
    registered keys use forward slashes, so the yielded dirpath stops matching
    the key the test registered.
    """
    fake = MockSafeOS()
    fake.add_file("/root/sub/deep/c.txt", "")
    dirpaths = [dirpath for dirpath, _, _ in fake.walk("/root")]
    assert dirpaths == ["/root", "/root/sub", "/root/sub/deep"]
    assert all("\\" not in p for p in dirpaths)


def test_glob_depth_is_separator_agnostic():
    """`*` must not cross a separator regardless of the platform's os.sep."""
    fake = MockSafeOS()
    fake.add_files({"/etc/dd/a.conf": "", "/etc/dd/sub/b.conf": ""})
    assert fake.glob("/etc/dd/*.conf") == ["/etc/dd/a.conf"]
    assert sorted(fake.glob("/etc/dd/**/*.conf", recursive=True)) == [
        "/etc/dd/a.conf",
        "/etc/dd/sub/b.conf",
    ]


@pytest.fixture
def windows_path_semantics(monkeypatch):
    """Make os.path behave as it does on Windows, on any host.

    The double is keyed by the paths callers register, which use forward
    slashes. Two Windows-only defects came from letting the platform separator
    into that key space, and neither was reproducible on POSIX. Simulating
    ntpath keeps that regression covered without a Windows runner.
    """
    import ntpath

    monkeypatch.setattr(os, 'path', ntpath)
    monkeypatch.setattr(os, 'sep', '\\')
    monkeypatch.setattr(os, 'altsep', '/')


def test_walk_under_windows_path_semantics(windows_path_semantics):
    fake = MockSafeOS()
    fake.add_file("/root/a.txt", "")
    fake.add_file("/root/sub/b.txt", "")
    fake.add_file("/root/sub/deep/c.txt", "")

    walked = {d: (sorted(dirs), sorted(files)) for d, dirs, files in fake.walk("/root")}
    assert sorted(walked) == ["/root", "/root/sub", "/root/sub/deep"]
    assert walked["/root"] == (["sub"], ["a.txt"])
    assert walked["/root/sub"] == (["deep"], ["b.txt"])


def test_glob_under_windows_path_semantics(windows_path_semantics):
    fake = MockSafeOS()
    fake.add_files({"/etc/dd/a.conf": "", "/etc/dd/sub/b.conf": "", "/etc/dd/c.txt": ""})
    assert fake.glob("/etc/dd/*.conf") == ["/etc/dd/a.conf"]
    assert sorted(fake.glob("/etc/dd/**/*.conf", recursive=True)) == [
        "/etc/dd/a.conf",
        "/etc/dd/sub/b.conf",
    ]


def test_listing_under_windows_path_semantics(windows_path_semantics):
    fake = MockSafeOS()
    fake.add_file("/root/a.txt", "")
    fake.add_file("/root/sub/b.txt", "")
    assert fake.listdir("/root") == ["a.txt", "sub"]
    with fake.scandir("/root") as entries:
        assert sorted(e.name for e in entries) == ["a.txt", "sub"]
