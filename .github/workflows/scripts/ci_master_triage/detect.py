#!/usr/bin/env python3
"""Detect and group failing master CI runs from the GitHub Actions API.

Deterministic and LLM-free: this script decides *whether* to alert and *how
severe* a breakage is. It groups failures by run/commit so one root cause
produces one alert instead of one alert per failing target.

Output contract (``triage_output.json`` + ``$GITHUB_OUTPUT``) is consumed by
``notify.py`` and the optional ``enrich.py`` LLM enrichment step.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

API_ROOT = "https://api.github.com"

# Reusable-workflow job names surface in the API as
#   "test / <job-id>[ (<matrix>)] / <leaf>"
# The job-id is the YAML key in test-all*.yml and our stable join key.
TEST_JOB_NAME_RE = re.compile(r"^test / (j[0-9a-f]+)(?: \(.*\))? / ")
JOB_KEY_RE = re.compile(r"^  (j[0-9a-f]+):\s*$")
JOB_NAME_RE = re.compile(r"^\s+job-name:\s*(.+?)\s*$")
TARGET_RE = re.compile(r"^\s+target:\s*(.+?)\s*$")

# A failure touching these targets means the shared base is broken, which
# usually cascades into every integration: always alert in real time.
BASE_PACKAGE_TARGETS = {
    "datadog_checks_base",
    "datadog_checks_dev",
    "datadog_checks_downloader",
    "ddev",
}

MASTER_WORKFLOWS = ("master.yml", "master-windows.yml")


class Severity:
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    NONE = "NONE"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def github_request(path: str, token: str) -> Any:
    """GET an absolute or repo-relative GitHub API path and decode JSON."""
    url = path if path.startswith("http") else f"{API_ROOT}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ci-master-triage",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def parse_target_map(repo_root: Path) -> dict[str, dict[str, str]]:
    """Map each test-target job-id to its human job-name and target slug."""
    mapping: dict[str, dict[str, str]] = {}
    for fname in ("test-all.yml", "test-all-windows.yml"):
        path = repo_root / ".github" / "workflows" / fname
        if not path.exists():
            continue
        current_id: str | None = None
        job_name: str | None = None
        for line in path.read_text().splitlines():
            key = JOB_KEY_RE.match(line)
            if key:
                current_id, job_name = key.group(1), None
                continue
            if current_id is None:
                continue
            name_match = JOB_NAME_RE.match(line)
            if name_match:
                job_name = name_match.group(1).strip("\"'")
                continue
            target_match = TARGET_RE.match(line)
            if target_match:
                target = target_match.group(1).strip("\"'")
                mapping[current_id] = {"job_name": job_name or current_id, "target": target}
                current_id = None
    return mapping


def iter_failed_jobs(run_id: int, token: str, repo: str) -> Iterator[dict[str, Any]]:
    """Yield the latest-attempt jobs of a run that ended in failure."""
    page = 1
    while True:
        payload = github_request(
            f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&filter=latest&page={page}",
            token,
        )
        jobs = payload.get("jobs", [])
        for job in jobs:
            if job.get("conclusion") == "failure":
                yield job
        if len(jobs) < 100:
            return
        page += 1


def classify(failed_targets: list[dict[str, str]], storm_threshold: int) -> str:
    """Severity for one run from its failed test targets."""
    if not failed_targets:
        return Severity.NONE
    if len(failed_targets) >= storm_threshold:
        return Severity.HIGH
    if any(t["target"] in BASE_PACKAGE_TARGETS for t in failed_targets):
        return Severity.HIGH
    return Severity.NORMAL


def build_run_record(
    run: dict[str, Any], token: str, repo: str, target_map: dict[str, dict[str, str]], storm_threshold: int
) -> dict[str, Any]:
    """Collect failed test-target jobs for a run and classify its severity."""
    failed_targets: list[dict[str, str]] = []
    other_failures = 0
    seen_job_ids: set[str] = set()
    for job in iter_failed_jobs(run["id"], token, repo):
        match = TEST_JOB_NAME_RE.match(job.get("name", ""))
        if not match:
            other_failures += 1
            continue
        job_id = match.group(1)
        if job_id in seen_job_ids:
            continue
        seen_job_ids.add(job_id)
        meta = target_map.get(job_id, {"job_name": job_id, "target": job_id})
        failed_targets.append(
            {
                "target": meta["target"],
                "job_name": meta["job_name"],
                "job_id": job_id,
                "gh_job_id": str(job.get("id", "")),
                "url": job.get("html_url", ""),
            }
        )
    failed_targets.sort(key=lambda t: t["job_name"].lower())
    return {
        "run_id": run["id"],
        "sha": run.get("head_sha", ""),
        "short_sha": run.get("head_sha", "")[:8],
        "title": run.get("display_title", ""),
        "actor": (run.get("actor") or {}).get("login", ""),
        "workflow": run.get("name", ""),
        "url": run.get("html_url", ""),
        "created_at": run.get("created_at", ""),
        "failed_targets": failed_targets,
        "failed_count": len(failed_targets),
        "other_failures": other_failures,
        "severity": classify(failed_targets, storm_threshold),
    }


def candidate_runs(token: str, repo: str, cutoff: datetime, explicit_ids: list[int]) -> Iterator[dict[str, Any]]:
    """Yield failed master runs to inspect: explicit IDs, or recent failures in-window."""
    if explicit_ids:
        for run_id in explicit_ids:
            yield github_request(f"/repos/{repo}/actions/runs/{run_id}", token)
        return
    for workflow in MASTER_WORKFLOWS:
        payload = github_request(
            f"/repos/{repo}/actions/workflows/{workflow}/runs"
            f"?branch=master&status=failure&per_page=50",
            token,
        )
        for run in payload.get("workflow_runs", []):
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created >= cutoff:
                yield run


def write_outputs(should_alert: bool, severity: str, run_count: int) -> None:
    out_path = env("GITHUB_OUTPUT")
    if not out_path:
        return
    with open(out_path, "a") as fh:
        fh.write(f"should_alert={'true' if should_alert else 'false'}\n")
        fh.write(f"severity={severity}\n")
        fh.write(f"run_count={run_count}\n")


def main() -> int:
    token = env("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    repo = env("GITHUB_REPOSITORY", "DataDog/integrations-core")
    mode = env("MODE", "digest")  # "realtime" or "digest"
    storm_threshold = int(env("STORM_THRESHOLD", "25"))
    repo_root = Path(env("REPO_ROOT", "."))
    state_file = Path(env("STATE_FILE", "ci_triage_state.json"))
    explicit_ids = [int(x) for x in env("EXPLICIT_RUN_IDS").split(",") if x.strip()]

    lookback = (
        timedelta(minutes=int(env("LOOKBACK_MINUTES", "45")))
        if mode == "realtime"
        else timedelta(hours=int(env("LOOKBACK_HOURS", "12")))
    )
    cutoff = datetime.now(timezone.utc) - lookback

    posted: set[int] = set()
    if state_file.exists():
        posted = set(json.loads(state_file.read_text()).get("posted_run_ids", []))

    target_map = parse_target_map(repo_root)
    records = [build_run_record(r, token, repo, target_map, storm_threshold) for r in candidate_runs(token, repo, cutoff, explicit_ids)]

    fresh = [r for r in records if r["run_id"] not in posted]
    if mode == "realtime":
        selected = [r for r in fresh if r["severity"] == Severity.HIGH]
    else:
        selected = [r for r in fresh if r["severity"] in (Severity.HIGH, Severity.NORMAL)]

    non_test_count = sum(1 for r in fresh if r["severity"] == Severity.NONE)
    overall = Severity.HIGH if any(r["severity"] == Severity.HIGH for r in selected) else (
        Severity.NORMAL if selected else Severity.NONE
    )

    enrichment_jobs: list[dict[str, str]] = []
    for record in selected:
        for target in record["failed_targets"][:8]:
            enrichment_jobs.append({"run_id": str(record["run_id"]), **target})

    output = {
        "mode": mode,
        "severity": overall,
        "runs": selected,
        "non_test_failure_count": non_test_count,
        "enrichment_jobs": enrichment_jobs[:8],
        "dashboard_url": env(
            "DASHBOARD_URL",
            "https://app-dev-prod.datadoghq.com/dashboard/knc-6sp-caq/agent-integrations-overview",
        ),
    }
    Path("triage_output.json").write_text(json.dumps(output, indent=2))

    should_alert = bool(selected)
    if should_alert and not explicit_ids:
        posted.update(r["run_id"] for r in selected)
        state_file.write_text(json.dumps({"posted_run_ids": sorted(posted)}))

    write_outputs(should_alert, overall, len(selected))
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
