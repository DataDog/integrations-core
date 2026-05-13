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
