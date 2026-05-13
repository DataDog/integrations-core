# Process Auto-Discovery Analysis Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `analysis/scripts/process_analyze.py`, a two-mode CLI that collects process-tree data from E2E environments and evaluates whether `isMainProcessForService` selects exactly one main process per service.

**Architecture:** A single Python file with `collect` and `analyze` subcommands. `collect` starts ddev environments, runs `disco --pid` for each container process, and saves JSON snapshots. `analyze` loads those snapshots, applies the algorithm, prints a verdict table, and writes a results JSON. The two modes are fully decoupled so the algorithm can be iterated without re-running environments.

**Tech Stack:** Python 3.12, stdlib only (`argparse`, `dataclasses`, `json`, `subprocess`, `pathlib`), `pytest` for tests.

---

## File Structure

| File | Purpose |
|------|---------|
| `analysis/scripts/process_analyze.py` | Single CLI tool — all logic |
| `analysis/scripts/tests/__init__.py` | Makes tests a package |
| `analysis/scripts/tests/test_process_analyze.py` | Unit tests |
| `analysis/process_autodiscovery/data/` | Created at runtime — collected JSON files |
| `analysis/process_autodiscovery/data/skipped.json` | Written by `collect` — skip log |
| `analysis/process_autodiscovery/results/` | Created at runtime — analysis output |

---

## Task 1: Scaffold — CLI, data types, test infrastructure

**Files:**
- Create: `analysis/scripts/process_analyze.py`
- Create: `analysis/scripts/tests/__init__.py`
- Create: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Create the test package init**

```bash
touch analysis/scripts/tests/__init__.py
```

- [ ] **Step 2: Write the failing import test**

Create `analysis/scripts/tests/test_process_analyze.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from process_analyze import Process, CollectedData, SkipEntry, ServiceVerdict, IntegrationResult


def test_imports():
    p = Process(pid=1, ppid=0, comm="nginx", cmdline="nginx", generated_name="nginx", has_service_data=True)
    assert p.pid == 1
```

- [ ] **Step 3: Run the test to confirm it fails**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core2
pytest analysis/scripts/tests/test_process_analyze.py -v
```

Expected: `ModuleNotFoundError: No module named 'process_analyze'`

- [ ] **Step 4: Create `process_analyze.py` with all data types and CLI scaffold**

Create `analysis/scripts/process_analyze.py`:

```python
#!/usr/bin/env python3
"""Analyze whether isMainProcessForService correctly identifies the main process
across integrations-core E2E environments."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "analysis" / "process_autodiscovery" / "data"
DEFAULT_RESULTS_DIR = REPO_ROOT / "analysis" / "process_autodiscovery" / "results"
DISCO_PATH = (
    Path.home() / "go/src/github.com/DataDog/datadog-agent/target/debug/disco"
)


@dataclasses.dataclass
class Process:
    pid: int
    ppid: int
    comm: str
    cmdline: str
    generated_name: str | None
    has_service_data: bool


@dataclasses.dataclass
class CollectedData:
    integration: str
    environment: str
    collected_at: str
    processes: list[Process]
    disco_raw: dict


@dataclasses.dataclass
class SkipEntry:
    integration: str
    reason: str
    skipped_at: str
    details: str


@dataclasses.dataclass
class ServiceVerdict:
    generated_name: str
    main_pids: list[int]
    skipped_pids: list[int]
    verdict: str


@dataclasses.dataclass
class IntegrationResult:
    integration: str
    environment: str
    services: list[ServiceVerdict]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze isMainProcessForService against real E2E environments"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    collect_p = sub.add_parser("collect", help="Collect process data from environments")
    collect_p.add_argument("integration", nargs="?", help="Single integration to collect")
    collect_p.add_argument("--all", action="store_true", help="Collect all integrations")
    collect_p.add_argument("--env", help="Override environment selection")
    collect_p.add_argument("--disco", default=str(DISCO_PATH), help="Path to disco binary")
    collect_p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Output directory")
    collect_p.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root")

    analyze_p = sub.add_parser("analyze", help="Analyze saved process data")
    analyze_p.add_argument("--integration", help="Limit to one integration")
    analyze_p.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Data directory")
    analyze_p.add_argument(
        "--results-dir", default=str(DEFAULT_RESULTS_DIR), help="Results output directory"
    )

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.command == "collect":
        cmd_collect(args)
    else:
        cmd_analyze(args)


def cmd_collect(args: argparse.Namespace) -> None:
    raise NotImplementedError


def cmd_analyze(args: argparse.Namespace) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the test to confirm it passes**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/__init__.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add process_analyze.py scaffold with data types and CLI"
```

---

## Task 2: Integration discovery and environment selection

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
from process_analyze import (
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "env_show or environment or e2e"
```

Expected: `ImportError` for the new names.

- [ ] **Step 3: Implement the three functions in `process_analyze.py`**

Add after the `now_iso()` function:

```python
def find_integrations_with_e2e(repo_root: Path) -> list[str]:
    """Return sorted list of integration names that have a test_e2e.py file."""
    return sorted(
        path.parts[-3]
        for path in repo_root.glob("*/tests/test_e2e.py")
    )


def parse_ddev_env_show(output: str) -> list[str]:
    """Extract environment names from `ddev env show` table output."""
    envs = []
    for line in output.splitlines():
        m = re.match(r"[│┤]\s+(\S+)\s+[│┤]", line)
        if m and m.group(1) != "Name":
            envs.append(m.group(1))
    return envs


def select_environment(envs: list[str]) -> str | None:
    """Return the last environment with a numeric version suffix, or the last overall."""
    if not envs:
        return None
    version_envs = [e for e in envs if re.search(r"-\d+\.\d+$", e)]
    return version_envs[-1] if version_envs else envs[-1]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "env_show or environment or e2e"
```

Expected: all 5 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add integration discovery and environment selection"
```

---

## Task 3: Fake caddy detection

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "caddy"
```

Expected: `ImportError` for `uses_caddy`.

- [ ] **Step 3: Implement `uses_caddy` in `process_analyze.py`**

Add after `select_environment`:

```python
def uses_caddy(integration: str, repo_root: Path) -> tuple[bool, str]:
    """Return (True, detail) if any YAML under tests/ uses a caddy image."""
    tests_dir = repo_root / integration / "tests"
    if not tests_dir.exists():
        return False, ""
    for ext in ("yaml", "yml"):
        for path in tests_dir.rglob(f"*.{ext}"):
            try:
                content = path.read_text(errors="replace")
            except OSError:
                continue
            m = re.search(r"image:\s*(caddy:\S+)", content)
            if m:
                rel = path.relative_to(repo_root)
                return True, f"image {m.group(1)} found in {rel}"
    return False, ""
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "caddy"
```

Expected: 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add fake caddy environment detection"
```

---

## Task 4: Process data collection from /proc and disco

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "proc or disco or collect_process"
```

Expected: `ImportError` for the new names.

- [ ] **Step 3: Implement the four functions in `process_analyze.py`**

Add after `uses_caddy`:

```python
def read_proc_status(pid: int) -> dict[str, str]:
    """Read /proc/<pid>/status and return key→value pairs."""
    result: dict[str, str] = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
    except (OSError, PermissionError):
        pass
    return result


def read_proc_cmdline(pid: int) -> str:
    """Read /proc/<pid>/cmdline, replacing null bytes with spaces."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    except (OSError, PermissionError):
        return ""


def run_disco(disco_path: str, pid: int) -> dict:
    """Run disco --pid <pid> and return parsed JSON. Returns empty response on any error."""
    try:
        result = subprocess.run(
            [disco_path, "--pid", str(pid)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        return {"services": [], "injected_pids": [], "gpu_pids": []}


def collect_process(pid: int, disco_path: str) -> Process | None:
    """Collect all data for a single PID. Returns None if the process has vanished."""
    status = read_proc_status(pid)
    if not status:
        return None
    ppid = int(status.get("PPid", 0))
    comm = status.get("Name", "")
    cmdline = read_proc_cmdline(pid)
    disco_result = run_disco(disco_path, pid)
    services = disco_result.get("services", [])
    if services:
        return Process(
            pid=pid,
            ppid=ppid,
            comm=comm,
            cmdline=cmdline,
            generated_name=services[0].get("generated_name"),
            has_service_data=True,
        )
    return Process(
        pid=pid,
        ppid=ppid,
        comm=comm,
        cmdline=cmdline,
        generated_name=None,
        has_service_data=False,
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "proc or disco or collect_process"
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add process data collection from /proc and disco"
```

---

## Task 5: Container PID discovery

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "container"
```

Expected: `ImportError` for new names.

- [ ] **Step 3: Implement the two functions in `process_analyze.py`**

Add a module-level constant and the two functions after `collect_process`:

```python
_proc_root = Path("/proc")


def get_current_container_ids() -> set[str]:
    """Return the set of short container IDs currently running."""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.ID}}"],
        capture_output=True,
        text=True,
    )
    return set(result.stdout.split())


def get_pids_in_container(container_name_or_id: str) -> list[int]:
    """Return all host PIDs whose cgroup references the given container."""
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.Id}}", container_name_or_id],
        capture_output=True,
        text=True,
    )
    full_id = result.stdout.strip()
    if not full_id:
        return []
    pids: list[int] = []
    for entry in _proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cgroup = (entry / "cgroup").read_text()
        except (OSError, PermissionError):
            continue
        if full_id in cgroup or full_id[:12] in cgroup:
            pids.append(int(entry.name))
    return pids
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "container"
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add container PID discovery via /proc cgroup files"
```

---

## Task 6: `is_main_process` algorithm

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
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
        (1, 0, "sh", False),   # parent: no service
        (5, 1, "nginx", True),  # child
    )
    assert is_main_process(5, procs) is True


def test_main_process_parent_same_name_is_not_main():
    procs = _procs(
        (1, 0, "nginx", True),  # master: ppid=0 → main
        (5, 1, "nginx", True),  # worker: parent has same name → not main
    )
    assert is_main_process(5, procs) is False


def test_main_process_parent_different_name_is_main():
    procs = _procs(
        (1, 0, "supervisord", True),
        (5, 1, "nginx", True),  # parent is supervisord, different name → main
    )
    assert is_main_process(5, procs) is True
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "main_process"
```

Expected: `ImportError` for `is_main_process`.

- [ ] **Step 3: Implement `is_main_process` in `process_analyze.py`**

Add after `get_pids_in_container`:

```python
def is_main_process(pid: int, processes: dict[int, Process]) -> bool:
    """Python equivalent of the Go isMainProcessForService function.

    Returns True if this process should be treated as the main (root) process
    for its service — i.e., it should get its own integration instance.
    """
    p = processes[pid]
    if p.ppid in (0, 1):
        return True
    parent = processes.get(p.ppid)
    if parent is None or not parent.has_service_data:
        return True
    return parent.generated_name != p.generated_name
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "main_process"
```

Expected: all 6 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add is_main_process algorithm with full branch coverage"
```

---

## Task 7: Data persistence

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "save or load or skip"
```

Expected: `ImportError` for the new names.

- [ ] **Step 3: Implement the four functions in `process_analyze.py`**

Add after `is_main_process`:

```python
def save_data(data: CollectedData, data_dir: Path) -> None:
    """Save collected process data to a JSON file."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{data.integration}__{data.environment}.json"
    with open(path, "w") as f:
        json.dump(dataclasses.asdict(data), f, indent=2)


def load_data(path: Path) -> CollectedData:
    """Load a collected process data file."""
    with open(path) as f:
        d = json.load(f)
    d["processes"] = [Process(**p) for p in d["processes"]]
    return CollectedData(**d)


def record_skip(data_dir: Path, entry: SkipEntry) -> None:
    """Append or update a skip entry in skipped.json."""
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "skipped.json"
    entries: list[dict] = []
    if path.exists():
        with open(path) as f:
            entries = json.load(f)
    new_entry = dataclasses.asdict(entry)
    for i, e in enumerate(entries):
        if e["integration"] == entry.integration:
            entries[i] = new_entry
            break
    else:
        entries.append(new_entry)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def load_skipped(data_dir: Path) -> list[SkipEntry]:
    """Load skip entries from skipped.json, or return empty list if absent."""
    path = data_dir / "skipped.json"
    if not path.exists():
        return []
    with open(path) as f:
        return [SkipEntry(**e) for e in json.load(f)]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "save or load or skip"
```

Expected: all 5 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add data persistence: save/load CollectedData and skip entries"
```

---

## Task 8: `collect` subcommand

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
from process_analyze import collect_integration


def test_collect_integration_skips_caddy(tmp_path):
    from process_analyze import SkipEntry
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "collect_integration"
```

Expected: `ImportError` for `collect_integration`.

- [ ] **Step 3: Implement `collect_integration` and `cmd_collect` in `process_analyze.py`**

Add after `load_skipped`, replacing the stub `cmd_collect`:

```python
def collect_integration(
    integration: str,
    env_override: str | None,
    disco_path: str,
    data_dir: Path,
    repo_root: Path,
) -> str:
    """Collect process data for one integration. Returns 'ok', 'skipped', or 'error'."""
    # 1. Select environment
    if env_override:
        env = env_override
    else:
        show = subprocess.run(
            ["ddev", "env", "show", integration],
            capture_output=True, text=True,
        )
        env = select_environment(parse_ddev_env_show(show.stdout))
    if env is None:
        record_skip(data_dir, SkipEntry(
            integration=integration,
            reason="no environments found",
            skipped_at=now_iso(),
            details="ddev env show returned no environments",
        ))
        return "skipped"

    # 2. Fake caddy check
    is_caddy, caddy_detail = uses_caddy(integration, repo_root)
    if is_caddy:
        record_skip(data_dir, SkipEntry(
            integration=integration,
            reason="fake caddy server",
            skipped_at=now_iso(),
            details=caddy_detail,
        ))
        return "skipped"

    # 3. Start environment
    before = get_current_container_ids()
    try:
        start = subprocess.run(
            ["ddev", "--no-interactive", "env", "start", "--dev", integration, env],
            capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        record_skip(data_dir, SkipEntry(
            integration=integration,
            reason="env start failed",
            skipped_at=now_iso(),
            details="ddev env start timed out after 300s",
        ))
        return "skipped"

    if start.returncode != 0:
        record_skip(data_dir, SkipEntry(
            integration=integration,
            reason="env start failed",
            skipped_at=now_iso(),
            details=f"exit code {start.returncode}: {start.stderr[:500]}",
        ))
        return "skipped"

    try:
        # 4. Find new containers
        new_ids = get_current_container_ids() - before

        # 5. Collect PIDs from all containers
        all_pids: list[int] = []
        for cid in new_ids:
            all_pids.extend(get_pids_in_container(cid))

        # 6. Collect process data
        processes: list[Process] = []
        for pid in all_pids:
            proc = collect_process(pid, disco_path)
            if proc is not None:
                processes.append(proc)

        # 7. Save
        data = CollectedData(
            integration=integration,
            environment=env,
            collected_at=now_iso(),
            processes=processes,
            disco_raw={},
        )
        save_data(data, data_dir)
        return "ok"

    finally:
        # 8. Stop environment regardless of success
        subprocess.run(
            ["ddev", "--no-interactive", "env", "stop", integration, env],
            capture_output=True, timeout=120,
        )


def cmd_collect(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo_root)
    data_dir = Path(args.data_dir)

    if args.all:
        integrations = find_integrations_with_e2e(repo_root)
    elif args.integration:
        integrations = [args.integration]
    else:
        print("Error: specify an integration name or --all", flush=True)
        raise SystemExit(1)

    for integration in integrations:
        print(f"[{integration}] ", end="", flush=True)
        status = collect_integration(
            integration=integration,
            env_override=args.env,
            disco_path=args.disco,
            data_dir=data_dir,
            repo_root=repo_root,
        )
        print(status, flush=True)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "collect_integration"
```

Expected: both tests `PASSED`

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add collect subcommand with caddy detection and skip tracking"
```

---

## Task 9: `analyze` subcommand and output formatting

**Files:**
- Modify: `analysis/scripts/process_analyze.py`
- Modify: `analysis/scripts/tests/test_process_analyze.py`

- [ ] **Step 1: Write failing tests**

Append to `analysis/scripts/tests/test_process_analyze.py`:

```python
from process_analyze import analyze_data, format_results_table


def _nginx_data() -> "CollectedData":
    from process_analyze import CollectedData, Process
    return CollectedData(
        integration="nginx",
        environment="py3.13-1.27",
        collected_at="2026-05-13T10:00:00+00:00",
        processes=[
            Process(1, 0, "nginx", "nginx: master", "nginx", True),
            Process(2, 1, "nginx", "nginx: worker", "nginx", True),
            Process(3, 1, "nginx", "nginx: worker", "nginx", True),
            Process(4, 0, "sh", "/bin/sh", None, False),
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
    assert svc.main_pids == [1]
    assert sorted(svc.skipped_pids) == [2, 3]
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
    from process_analyze import SkipEntry
    skipped = [SkipEntry("vault", "env start failed", "2026-05-13T10:00:00+00:00", "exit 1")]
    table = format_results_table(results, skipped)
    assert "nginx" in table
    assert "PASS" in table
    assert "vault" in table
    assert "env start failed" in table
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "analyze_data or format_results"
```

Expected: `ImportError` for new names.

- [ ] **Step 3: Implement `analyze_data`, `format_results_table`, and `cmd_analyze` in `process_analyze.py`**

Add after `cmd_collect`, replacing the stub `cmd_analyze`:

```python
def analyze_data(data: CollectedData) -> IntegrationResult:
    """Apply is_main_process to all service processes and compute verdicts."""
    by_pid = {p.pid: p for p in data.processes}
    service_procs = [p for p in data.processes if p.has_service_data]

    by_name: dict[str, list[Process]] = {}
    for p in service_procs:
        by_name.setdefault(p.generated_name or "", []).append(p)

    verdicts: list[ServiceVerdict] = []
    for name, procs in by_name.items():
        main_pids = [p.pid for p in procs if is_main_process(p.pid, by_pid)]
        skipped_pids = [p.pid for p in procs if not is_main_process(p.pid, by_pid)]
        n = len(main_pids)
        verdict = "PASS" if n == 1 else f"WARN (N={n})"
        verdicts.append(ServiceVerdict(
            generated_name=name,
            main_pids=main_pids,
            skipped_pids=skipped_pids,
            verdict=verdict,
        ))

    return IntegrationResult(
        integration=data.integration,
        environment=data.environment,
        services=verdicts,
    )


def format_results_table(
    results: list[IntegrationResult], skipped: list[SkipEntry]
) -> str:
    """Format analysis results as a human-readable table."""
    lines: list[str] = []
    col = (28, 18, 20, 20, 16)
    header = (
        f"{'Integration':<{col[0]}}"
        f"{'Environment':<{col[1]}}"
        f"{'Service':<{col[2]}}"
        f"{'Main PIDs':<{col[3]}}"
        f"{'Verdict':<{col[4]}}"
    )
    lines.append(header)
    lines.append("-" * sum(col))

    for r in results:
        if not r.services:
            lines.append(
                f"{r.integration:<{col[0]}}{r.environment:<{col[1]}}"
                f"{'(no services detected)':<{col[2]}}"
                f"{'[]':<{col[3]}}{'N/A':<{col[4]}}"
            )
            continue
        for svc in r.services:
            lines.append(
                f"{r.integration:<{col[0]}}{r.environment:<{col[1]}}"
                f"{svc.generated_name:<{col[2]}}"
                f"{str(svc.main_pids):<{col[3]}}"
                f"{svc.verdict:<{col[4]}}"
            )

    if skipped:
        lines.append("")
        lines.append(f"Skipped ({len(skipped)}):")
        for s in skipped:
            lines.append(f"  {s.integration:<40} — {s.reason}")

    return "\n".join(lines)


def cmd_analyze(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    data_files = sorted(f for f in data_dir.glob("*.json") if f.name != "skipped.json")
    if args.integration:
        data_files = [f for f in data_files if f.stem.startswith(args.integration + "__")]

    results: list[IntegrationResult] = []
    for path in data_files:
        data = load_data(path)
        results.append(analyze_data(data))

    skipped = load_skipped(data_dir)
    if args.integration:
        skipped = [s for s in skipped if s.integration == args.integration]

    print(format_results_table(results, skipped))

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    output_path = results_dir / f"analysis_{timestamp}.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "analyzed_at": now_iso(),
                "results": [dataclasses.asdict(r) for r in results],
                "skipped": [dataclasses.asdict(s) for s in skipped],
            },
            f,
            indent=2,
        )
    print(f"\nResults saved to {output_path}")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v -k "analyze_data or format_results"
```

Expected: all 5 tests `PASSED`

- [ ] **Step 5: Run the full test suite**

```bash
pytest analysis/scripts/tests/test_process_analyze.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add analysis/scripts/process_analyze.py analysis/scripts/tests/test_process_analyze.py
git commit -m "Add analyze subcommand with verdict table and JSON output"
```

---

## Task 10: End-to-end smoke test with nginx

This task verifies the complete tool against a real E2E environment. It is not automated — run it manually and inspect the output.

- [ ] **Step 1: Collect data for nginx**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core2
python analysis/scripts/process_analyze.py collect nginx \
    --disco /home/bits/go/src/github.com/DataDog/datadog-agent/target/debug/disco
```

Expected: `[nginx] ok` printed to stdout.

Verify the output file was created:
```bash
ls analysis/process_autodiscovery/data/nginx__*.json
```

Inspect the collected data:
```bash
cat analysis/process_autodiscovery/data/nginx__*.json | python3 -m json.tool | head -60
```

Check that processes were found and at least some have `has_service_data: true`.

- [ ] **Step 2: Run the analyze command**

```bash
python analysis/scripts/process_analyze.py analyze
```

Expected output: a table with an `nginx` row showing verdict (PASS or WARN).

Verify the results JSON was written:
```bash
ls analysis/process_autodiscovery/results/analysis_*.json
```

- [ ] **Step 3: Inspect and record findings**

If the verdict is `WARN`, examine the process tree to understand why:

```bash
# See all processes in the collected data and their is_main result
python3 - <<'EOF'
import json, sys
sys.path.insert(0, 'analysis/scripts')
from process_analyze import load_data, is_main_process
from pathlib import Path

for path in sorted(Path('analysis/process_autodiscovery/data').glob('*.json')):
    if path.name == 'skipped.json':
        continue
    data = load_data(path)
    by_pid = {p.pid: p for p in data.processes}
    print(f"\n=== {data.integration} / {data.environment} ===")
    for p in data.processes:
        if p.has_service_data:
            main = is_main_process(p.pid, by_pid)
            print(f"  pid={p.pid} ppid={p.ppid} comm={p.comm!r} name={p.generated_name!r} main={main}")
EOF
```

- [ ] **Step 4: Commit data directories (gitkeep) and verify script is executable**

```bash
mkdir -p analysis/process_autodiscovery/data analysis/process_autodiscovery/results
touch analysis/process_autodiscovery/data/.gitkeep analysis/process_autodiscovery/results/.gitkeep
chmod +x analysis/scripts/process_analyze.py
git add analysis/process_autodiscovery/data/.gitkeep analysis/process_autodiscovery/results/.gitkeep
git add analysis/scripts/process_analyze.py
git commit -m "Add process_autodiscovery data and results directories"
```
