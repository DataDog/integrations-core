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
    collect_integration,
    analyze_data,
    format_results_table,
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


from process_analyze import is_main_process


def _procs(*args: tuple) -> dict[int, "Process"]:
    """Build a pid→Process dict from (pid, ppid, name, has_service) tuples."""
    from process_analyze import Process
    return {
        pid: Process(pid=pid, ppid=ppid, comm=name, cmdline=name,
                     generated_name=name if has_svc else None,
                     has_service_data=has_svc)
        for pid, ppid, name, has_svc in args
    }


def test_main_process_ppid_zero():
    procs = _procs((5, 0, "nginx", True))
    assert is_main_process(5, procs) is True


def test_main_process_ppid_one():
    procs = _procs((5, 1, "nginx", True))
    assert is_main_process(5, procs) is True


def test_main_process_parent_not_in_store():
    procs = _procs((5, 99, "nginx", True))  # parent 99 not in dict
    assert is_main_process(5, procs) is True


def test_main_process_parent_has_no_service():
    procs = _procs(
        (50, 2, "sh", False),   # parent: no service data
        (5, 50, "nginx", True), # child whose parent has no service → main
    )
    assert is_main_process(5, procs) is True


def test_main_process_parent_same_name_is_not_main():
    procs = _procs(
        (100, 0, "nginx", True),  # master: ppid=0 → main
        (5, 100, "nginx", True),  # worker: ppid=100 (master), same name → not main
    )
    assert is_main_process(5, procs) is False


def test_main_process_parent_different_name_is_main():
    procs = _procs(
        (1, 0, "supervisord", True),
        (5, 1, "nginx", True),  # parent is supervisord, different name → main
    )
    assert is_main_process(5, procs) is True


from process_analyze import save_data, load_data, record_skip, load_skipped


def _sample_data() -> "CollectedData":
    from process_analyze import CollectedData, Process
    return CollectedData(
        integration="nginx",
        environment="py3.13-1.27",
        collected_at="2026-05-13T10:00:00+00:00",
        processes=[
            Process(pid=1, ppid=0, comm="nginx", cmdline="nginx: master",
                    generated_name="nginx", has_service_data=True),
            Process(pid=2, ppid=1, comm="nginx", cmdline="nginx: worker",
                    generated_name="nginx", has_service_data=True),
        ],
        disco_raw={},
    )


def test_save_and_load_round_trip(tmp_path):
    data = _sample_data()
    save_data(data, tmp_path)
    path = tmp_path / "nginx__py3.13-1.27.json"
    assert path.exists()
    loaded = load_data(path)
    assert loaded.integration == "nginx"
    assert len(loaded.processes) == 2
    assert loaded.processes[0].comm == "nginx"
    assert loaded.processes[0].has_service_data is True


def test_record_skip_creates_file(tmp_path):
    from process_analyze import SkipEntry
    entry = SkipEntry(
        integration="vault",
        reason="env start failed",
        skipped_at="2026-05-13T10:05:00+00:00",
        details="exit code 1",
    )
    record_skip(tmp_path, entry)
    path = tmp_path / "skipped.json"
    assert path.exists()
    skipped = load_skipped(tmp_path)
    assert len(skipped) == 1
    assert skipped[0].integration == "vault"


def test_record_skip_upserts(tmp_path):
    from process_analyze import SkipEntry
    e1 = SkipEntry("vault", "env start failed", "2026-05-13T10:00:00+00:00", "first")
    e2 = SkipEntry("vault", "env start failed", "2026-05-13T11:00:00+00:00", "updated")
    record_skip(tmp_path, e1)
    record_skip(tmp_path, e2)
    skipped = load_skipped(tmp_path)
    assert len(skipped) == 1
    assert skipped[0].details == "updated"


def test_load_skipped_missing_file(tmp_path):
    skipped = load_skipped(tmp_path)
    assert skipped == []


def test_collect_integration_skips_caddy(tmp_path):
    # Create a fake integration with caddy compose
    tests_dir = tmp_path / "mycheck" / "tests" / "docker"
    tests_dir.mkdir(parents=True)
    (tests_dir / "docker-compose.yaml").write_text(
        "services:\n  app:\n    image: caddy:2.7\n"
    )

    data_dir = tmp_path / "data"
    # Pass env_override to skip the ddev env show subprocess call
    result = collect_integration("mycheck", "py3.13-1.0", "/fake/disco", data_dir, tmp_path)
    assert result == "skipped"
    skipped = load_skipped(data_dir)
    assert skipped[0].reason == "fake caddy server"


def test_collect_integration_skips_on_env_start_failure(tmp_path):
    (tmp_path / "mycheck" / "tests").mkdir(parents=True)
    data_dir = tmp_path / "data"
    with patch("subprocess.run") as mock_run:
        # Calls in order:
        #   1. ddev env show  (env selection)
        #   2. docker ps      (get_current_container_ids, before snapshot)
        #   3. ddev env start — fail
        mock_run.side_effect = [
            MagicMock(stdout="│ py3.13-1.0 │\n", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", stderr="docker error", returncode=1),
        ]
        result = collect_integration("mycheck", None, "/fake/disco", data_dir, tmp_path)
    assert result == "skipped"
    skipped = load_skipped(data_dir)
    assert skipped[0].reason == "env start failed"


def _nginx_data() -> "CollectedData":
    from process_analyze import CollectedData, Process
    return CollectedData(
        integration="nginx",
        environment="py3.13-1.27",
        collected_at="2026-05-13T10:00:00+00:00",
        processes=[
            Process(100, 0, "nginx", "nginx: master", "nginx", True),
            Process(101, 100, "nginx", "nginx: worker", "nginx", True),
            Process(102, 100, "nginx", "nginx: worker", "nginx", True),
            Process(103, 0, "sh", "/bin/sh", None, False),
        ],
        disco_raw={},
    )


def test_analyze_data_nginx_pass():
    data = _nginx_data()
    result = analyze_data(data)
    assert result.integration == "nginx"
    assert len(result.services) == 1
    svc = result.services[0]
    assert svc.generated_name == "nginx"
    assert svc.main_pids == [100]
    assert sorted(svc.skipped_pids) == [101, 102]
    assert svc.verdict == "PASS"


def test_analyze_data_warn_too_many():
    from process_analyze import CollectedData, Process
    # All three processes are roots (ppid=0) with same name → 3 mains
    data = CollectedData(
        integration="bad",
        environment="py3.13-1.0",
        collected_at="2026-05-13T10:00:00+00:00",
        processes=[
            Process(1, 0, "myapp", "myapp", "myapp", True),
            Process(2, 0, "myapp", "myapp", "myapp", True),
            Process(3, 0, "myapp", "myapp", "myapp", True),
        ],
        disco_raw={},
    )
    result = analyze_data(data)
    assert result.services[0].verdict == "WARN (N=3)"


def test_analyze_data_spawned_by_different_service():
    from process_analyze import CollectedData, Process
    # nginx spawned by supervisord — parent has a different GeneratedName, so nginx is main
    data = CollectedData(
        integration="test",
        environment="py3.13-1.0",
        collected_at="2026-05-13T10:00:00+00:00",
        processes=[
            Process(1, 0, "supervisord", "supervisord", "supervisord", True),
            Process(2, 1, "nginx", "nginx: master", "nginx", True),
            Process(3, 2, "nginx", "nginx: worker", "nginx", True),
        ],
        disco_raw={},
    )
    result = analyze_data(data)
    nginx = next(s for s in result.services if s.generated_name == "nginx")
    assert nginx.verdict == "PASS"
    assert nginx.main_pids == [2]
    assert nginx.skipped_pids == [3]


def test_format_results_table_contains_integration():
    from process_analyze import IntegrationResult, ServiceVerdict
    results = [
        IntegrationResult(
            integration="nginx",
            environment="py3.13-1.27",
            services=[ServiceVerdict("nginx", [1], [2, 3], "PASS")],
        )
    ]
    skipped = [SkipEntry("vault", "env start failed", "2026-05-13T10:00:00+00:00", "exit 1")]
    table = format_results_table(results, skipped)
    assert "nginx" in table
    assert "PASS" in table
    assert "vault" in table
    assert "env start failed" in table
