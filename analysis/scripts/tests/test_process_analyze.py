import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from process_analyze import (
    Process,
    CollectedData,
    SkipEntry,
    ServiceVerdict,
    IntegrationResult,
    find_integrations_with_e2e,
    parse_ddev_env_show,
    select_environment,
)


SAMPLE_DDEV_ENV_SHOW = """\
Available
┏━━━━━━━━━━━━━┓
┃ Name        ┃
┡━━━━━━━━━━━━━┩
│ py3.13-1.12 │
├─────────────┤
│ py3.13-1.13 │
├─────────────┤
│ py3.13-1.27 │
├─────────────┤
│ py3.13-vts  │
└─────────────┘
"""


def test_imports():
    p = Process(pid=1, ppid=0, comm="nginx", cmdline="nginx", generated_name="nginx", has_service_data=True)
    assert p.pid == 1


def test_parse_ddev_env_show():
    envs = parse_ddev_env_show(SAMPLE_DDEV_ENV_SHOW)
    assert envs == ["py3.13-1.12", "py3.13-1.13", "py3.13-1.27", "py3.13-vts"]


def test_select_environment_prefers_version():
    envs = ["py3.13-1.12", "py3.13-1.13", "py3.13-1.27", "py3.13-vts"]
    assert select_environment(envs) == "py3.13-1.27"


def test_select_environment_falls_back_to_last():
    envs = ["py3.13-vts", "py3.13-plus"]
    assert select_environment(envs) == "py3.13-plus"


def test_select_environment_empty():
    assert select_environment([]) is None


def test_find_integrations_with_e2e(tmp_path):
    # Create fake integration directories
    for name in ["nginx", "redis", "no_e2e"]:
        tests = tmp_path / name / "tests"
        tests.mkdir(parents=True)
        if name != "no_e2e":
            (tests / "test_e2e.py").touch()

    result = find_integrations_with_e2e(tmp_path)
    assert result == ["nginx", "redis"]


from process_analyze import uses_caddy


def test_uses_caddy_detects_caddy_image(tmp_path):
    nginx_tests = tmp_path / "nginx" / "tests" / "docker"
    nginx_tests.mkdir(parents=True)
    (nginx_tests / "docker-compose.yaml").write_text(
        "services:\n  app:\n    image: caddy:2.7\n"
    )
    found, detail = uses_caddy("nginx", tmp_path)
    assert found is True
    assert "caddy:2.7" in detail


def test_uses_caddy_ignores_real_service(tmp_path):
    apache_tests = tmp_path / "apache" / "tests" / "compose"
    apache_tests.mkdir(parents=True)
    (apache_tests / "apache.yaml").write_text(
        "services:\n  apache:\n    image: httpd:2.4\n"
    )
    found, _ = uses_caddy("apache", tmp_path)
    assert found is False


def test_uses_caddy_no_tests_dir(tmp_path):
    found, _ = uses_caddy("nonexistent", tmp_path)
    assert found is False


from process_analyze import read_proc_status, read_proc_cmdline, run_disco, collect_process


def test_read_proc_status():
    import os, process_analyze as pa
    status = pa.read_proc_status(os.getpid())
    assert "Name" in status
    assert "PPid" in status


def test_read_proc_status_nonexistent_pid():
    import process_analyze as pa
    assert pa.read_proc_status(99999999) == {}


def test_read_proc_cmdline_null_separated():
    # Read current process cmdline — will have null separators or already decoded
    import process_analyze as pa
    import os
    cmdline = pa.read_proc_cmdline(os.getpid())
    assert len(cmdline) > 0


def test_run_disco_parses_json():
    fake_output = json.dumps({
        "services": [{"pid": 42, "generated_name": "nginx", "generated_name_source": "command_line",
                      "additional_generated_names": [], "tcp_ports": [80]}],
        "injected_pids": [],
        "gpu_pids": [],
    })
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=fake_output, returncode=0)
        import process_analyze as pa
        result = pa.run_disco("/fake/disco", 42)
    assert result["services"][0]["generated_name"] == "nginx"


def test_run_disco_returns_empty_on_failure():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        import process_analyze as pa
        result = pa.run_disco("/nonexistent/disco", 42)
    assert result == {"services": [], "injected_pids": [], "gpu_pids": []}


def test_collect_process_with_service():
    fake_disco = json.dumps({
        "services": [{"pid": 42, "generated_name": "nginx", "generated_name_source": "cmd",
                      "additional_generated_names": [], "tcp_ports": []}],
        "injected_pids": [],
        "gpu_pids": [],
    })
    import os, process_analyze as pa
    pid = os.getpid()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=fake_disco, returncode=0)
        proc = pa.collect_process(pid, "/fake/disco")
    assert proc is not None
    assert proc.has_service_data is True
    assert proc.generated_name == "nginx"
    assert proc.pid == pid


def test_collect_process_without_service():
    fake_disco = json.dumps({"services": [], "injected_pids": [], "gpu_pids": []})
    import os, process_analyze as pa
    pid = os.getpid()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=fake_disco, returncode=0)
        proc = pa.collect_process(pid, "/fake/disco")
    assert proc is not None
    assert proc.has_service_data is False
    assert proc.generated_name is None


from process_analyze import get_current_container_ids, get_pids_in_container


def test_get_current_container_ids_empty():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        import process_analyze as pa
        ids = pa.get_current_container_ids()
    assert ids == set()


def test_get_current_container_ids_parses_ids():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="abc123\ndef456\n", returncode=0)
        import process_analyze as pa
        ids = pa.get_current_container_ids()
    assert ids == {"abc123", "def456"}


def test_get_pids_in_container(tmp_path):
    # Build fake /proc structure with two PIDs in the container
    container_id = "a" * 64
    for pid, in_container in [(100, True), (101, False), (102, True)]:
        proc_dir = tmp_path / str(pid)
        proc_dir.mkdir()
        if in_container:
            cgroup = f"0::/system.slice/docker-{container_id}.scope\n"
        else:
            cgroup = "0::/system.slice/other.scope\n"
        (proc_dir / "cgroup").write_text(cgroup)

    import process_analyze as pa
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=container_id + "\n", returncode=0)
        with patch.object(pa, "_proc_root", tmp_path):
            pids = pa.get_pids_in_container("abc123")
    assert sorted(pids) == [100, 102]
