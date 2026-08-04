# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
from unittest import mock

import pytest

from datadog_checks.base.stubs.os_interface import METHOD_NAMES, MockOSInterface

pytestmark = pytest.mark.unit


def test_methods_are_mocks():
    fake = MockOSInterface()
    for name in METHOD_NAMES:
        assert isinstance(getattr(fake, name), mock.MagicMock)

    # Unconfigured subprocess methods stay bare MagicMocks: callable and recording.
    fake.which("ls")
    fake.which.assert_called_with("ls")


def test_add_file_predicates_and_read():
    fake = MockOSInterface()
    fake.add_file("/etc/app/conf.yaml", "key: value")

    assert fake.exists("/etc/app/conf.yaml") is True
    assert fake.isfile("/etc/app/conf.yaml") is True
    assert fake.isdir("/etc/app/conf.yaml") is False
    assert fake.getsize("/etc/app/conf.yaml") == len("key: value")

    with fake.open("/etc/app/conf.yaml") as f:
        assert f.read() == "key: value"


def test_add_file_registers_parent_dirs():
    fake = MockOSInterface()
    fake.add_file("/a/b/c.txt", "x")

    assert fake.isdir("/a") is True
    assert fake.isdir("/a/b") is True
    assert fake.exists("/a/b") is True
    assert fake.listdir("/a/b") == ["c.txt"]


def test_trailing_slash_normalized():
    fake = MockOSInterface()
    fake.add_dir("/data/")
    assert fake.isdir("/data") is True
    assert fake.isdir("/data/") is True


def test_open_read_missing_file_raises():
    fake = MockOSInterface()
    with pytest.raises(FileNotFoundError):
        fake.open("/nope")


def test_open_binary_read():
    fake = MockOSInterface()
    fake.add_file("/blob", b"\x00\x01\x02")
    with fake.open("/blob", "rb") as f:
        assert f.read() == b"\x00\x01\x02"


def test_open_write_captures_content():
    fake = MockOSInterface()
    with fake.open("/out.txt", "w") as f:
        f.write("hello")
    assert fake.get_file("/out.txt") == "hello"


def test_open_append_preserves_existing():
    fake = MockOSInterface()
    fake.add_file("/log", "line1\n")
    with fake.open("/log", "a") as f:
        f.write("line2\n")
    assert fake.get_file("/log") == "line1\nline2\n"


def test_open_is_line_iterable():
    fake = MockOSInterface()
    fake.add_file("/status", "NSpid:\t42 7\nName:\tx\n")
    with fake.open("/status") as f:
        lines = list(f)
    assert lines[0].startswith("NSpid:")


def test_listdir_lists_files_and_dirs():
    fake = MockOSInterface()
    fake.add_file("/base/f1", "")
    fake.add_dir("/base/sub")
    assert fake.listdir("/base") == ["f1", "sub"]


def test_listdir_missing_dir_raises():
    fake = MockOSInterface()
    with pytest.raises(FileNotFoundError):
        fake.listdir("/missing")


def test_scandir_is_context_manager_with_entries():
    fake = MockOSInterface()
    fake.add_file("/proc/42/status", "")
    fake.add_dir("/proc/42")

    with fake.scandir("/proc") as entries:
        names = {(e.name, e.is_dir()) for e in entries}
    assert ("42", True) in names


def test_walk_traverses_tree():
    fake = MockOSInterface()
    fake.add_file("/root/a.txt", "")
    fake.add_file("/root/sub/b.txt", "")

    walked = {dirpath: (sorted(dirs), sorted(files)) for dirpath, dirs, files in fake.walk("/root")}
    assert walked["/root"] == (["sub"], ["a.txt"])
    assert walked["/root/sub"] == ([], ["b.txt"])


def test_set_command_output_get_subprocess_output():
    fake = MockOSInterface()
    fake.set_command_output("netstat -i", stdout="iface data", returncode=0)

    out, err, code = fake.get_subprocess_output("netstat -i", None)
    assert (out, err, code) == ("iface data", "", 0)


def test_set_command_output_matches_list_command():
    fake = MockOSInterface()
    fake.set_command_output(["ps", "aux"], stdout="procs")
    out, _, _ = fake.get_subprocess_output(["ps", "aux"], None)
    assert out == "procs"


def test_set_command_output_run_returns_completed_process():
    fake = MockOSInterface()
    fake.set_command_output("lparstat -m", stdout="mem", returncode=0)

    proc = fake.run(["lparstat", "-m"], text=True)
    assert isinstance(proc, subprocess.CompletedProcess)
    assert proc.returncode == 0
    assert proc.stdout == "mem"


def test_run_bytes_when_not_text():
    fake = MockOSInterface()
    fake.set_command_output("lparstat -m", stdout="mem")
    proc = fake.run(["lparstat", "-m"])
    assert proc.stdout == b"mem"


def test_direct_mock_configuration_still_works():
    # The layer must not get in the way of raw mock usage.
    fake = MockOSInterface()
    fake.get_subprocess_output.return_value = ("x", "", 0)
    assert fake.get_subprocess_output("anything", None) == ("x", "", 0)

    fake.popen.side_effect = [mock_proc := object(), object()]
    assert fake.popen(["a"]) is mock_proc
    fake.popen.assert_called()
