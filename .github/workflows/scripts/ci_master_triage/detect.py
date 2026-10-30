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
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from common import FailedTarget, RunRecord, Severity, TriageOutput, env, parse_github_timestamp

API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT = 30

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

# Drop dedup state older than this so the persisted set can't grow without
# bound. Must comfortably exceed the largest lookback window (18h digest) so a
# run still in a lookback window is never pruned and re-alerted.
STATE_RETENTION_HOURS = 72


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
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
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


def classify(failed_targets: list[FailedTarget], storm_threshold: int) -> Severity:
    """Severity for one run from its failed test targets."""
    if not failed_targets:
        return Severity.NONE
    total_legs = sum(t["leg_count"] for t in failed_targets)
    if len(failed_targets) >= storm_threshold or total_legs >= storm_threshold:
        return Severity.HIGH
    if any(t["target"] in BASE_PACKAGE_TARGETS for t in failed_targets):
        return Severity.HIGH
    return Severity.NORMAL


def build_run_record(
    run: dict[str, Any], token: str, repo: str, target_map: dict[str, dict[str, str]], storm_threshold: int
) -> RunRecord:
    """Collect failed test-target jobs for a run and classify its severity.

    Matrix legs of one target share a reusable-workflow job-id, so they collapse
    to a single target entry whose ``leg_count`` records how many legs failed.
    """
    target_records: dict[str, FailedTarget] = {}
    other_failures = 0
    for job in iter_failed_jobs(run["id"], token, repo):
        match = TEST_JOB_NAME_RE.match(job.get("name", ""))
        if not match:
            other_failures += 1
            continue
        job_id = match.group(1)
        record = target_records.get(job_id)
        if record is None:
            meta = target_map.get(job_id, {"job_name": job_id, "target": job_id})
            record = {
                "target": meta["target"],
                "job_name": meta["job_name"],
                "job_id": job_id,
                "gh_job_id": str(job.get("id", "")),
                "url": job.get("html_url", ""),
                "leg_count": 0,
            }
            target_records[job_id] = record
        record["leg_count"] += 1
    failed_targets = sorted(target_records.values(), key=lambda t: t["job_name"].lower())
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
        page = 1
        while True:
            payload = github_request(
                f"/repos/{repo}/actions/workflows/{workflow}/runs"
                f"?branch=master&status=failure&per_page=100&page={page}",
                token,
            )
            runs = payload.get("workflow_runs", [])
            reached_cutoff = False
            for run in runs:
                created = parse_github_timestamp(run["created_at"])
                if created < cutoff:
                    # Results are newest-first, so nothing past here is in-window.
                    reached_cutoff = True
                    break
                yield run
            if reached_cutoff or len(runs) < 100:
                return
            page += 1


def select_runs(records: list[RunRecord], mode: str, posted: dict[int, str]) -> list[RunRecord]:
    """Pick the fresh runs worth alerting on for this mode, worst-severity first."""
    fresh = [r for r in records if r["run_id"] not in posted]
    if mode == "realtime":
        selected = [r for r in fresh if r["severity"] == Severity.HIGH]
    else:
        selected = [r for r in fresh if r["severity"] in (Severity.HIGH, Severity.NORMAL)]
    selected.sort(key=lambda r: 0 if r["severity"] == Severity.HIGH else 1)
    return selected


def overall_severity(selected: list[RunRecord]) -> Severity:
    """Roll the selected runs up to a single alert severity."""
    if any(r["severity"] == Severity.HIGH for r in selected):
        return Severity.HIGH
    return Severity.NORMAL if selected else Severity.NONE


def load_posted_state(state_file: Path) -> dict[int, str]:
    """Read the run_id -> created_at dedup map, tolerating the legacy list format."""
    if not state_file.exists():
        return {}
    raw = json.loads(state_file.read_text())
    posted = raw.get("posted")
    if isinstance(posted, dict):
        return {int(k): v for k, v in posted.items()}
    # Legacy format: a bare list of ids with no timestamps.
    return {int(rid): "" for rid in raw.get("posted_run_ids", [])}


def prune_posted(posted: dict[int, str], now: datetime) -> dict[int, str]:
    """Drop entries older than the retention window (undated entries are kept once)."""
    horizon = now - timedelta(hours=STATE_RETENTION_HOURS)
    kept: dict[int, str] = {}
    for run_id, created_at in posted.items():
        if not created_at:
            kept[run_id] = now.isoformat()
            continue
        try:
            created = parse_github_timestamp(created_at)
        except ValueError:
            kept[run_id] = now.isoformat()
            continue
        if created >= horizon:
            kept[run_id] = created_at
    return kept


def build_enrichment_jobs(selected: list[RunRecord], limit: int = 8) -> list[dict[str, str]]:
    """Flatten failed targets into enrichment jobs, capped globally at ``limit``.

    The cap bounds log volume and Claude cost; ``selected`` is severity-sorted so
    the budget is spent on the most severe runs first.
    """
    jobs: list[dict[str, str]] = []
    for record in selected:
        for target in record["failed_targets"]:
            jobs.append({"run_id": str(record["run_id"]), **target})
    return jobs[:limit]


def write_outputs(should_alert: bool, severity: Severity, run_count: int) -> None:
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
    try:
        explicit_ids = [int(x) for x in env("EXPLICIT_RUN_IDS").split(",") if x.strip()]
    except ValueError as exc:
        print(f"EXPLICIT_RUN_IDS must be a comma-separated list of ints: {exc}", file=sys.stderr)
        return 1

    lookback = (
        timedelta(minutes=int(env("LOOKBACK_MINUTES", "45")))
        if mode == "realtime"
        else timedelta(hours=int(env("LOOKBACK_HOURS", "18")))
    )
    now = datetime.now(timezone.utc)
    cutoff = now - lookback

    posted = load_posted_state(state_file)
    target_map = parse_target_map(repo_root)
    records = [
        build_run_record(r, token, repo, target_map, storm_threshold)
        for r in candidate_runs(token, repo, cutoff, explicit_ids)
    ]

    selected = select_runs(records, mode, posted)
    non_test_count = sum(1 for r in records if r["run_id"] not in posted and r["severity"] == Severity.NONE)
    overall = overall_severity(selected)

    output: TriageOutput = {
        "mode": mode,
        "severity": overall,
        "runs": selected,
        "non_test_failure_count": non_test_count,
        "enrichment_jobs": build_enrichment_jobs(selected),
        "dashboard_url": env(
            "DASHBOARD_URL",
            "https://app-dev-prod.datadoghq.com/dashboard/knc-6sp-caq/agent-integrations-overview",
        ),
    }
    Path("triage_output.json").write_text(json.dumps(output, indent=2))

    should_alert = bool(selected)
    if should_alert and not explicit_ids:
        for record in selected:
            posted[record["run_id"]] = record["created_at"] or now.isoformat()
        posted = prune_posted(posted, now)
        state_file.write_text(json.dumps({"posted": {str(k): v for k, v in posted.items()}}))

    write_outputs(should_alert, overall, len(selected))
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
