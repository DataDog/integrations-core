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
