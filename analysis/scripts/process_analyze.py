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
