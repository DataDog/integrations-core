# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck
    from datadog_checks.control_m.client import ControlMClient

STATUS_NORMALIZATION: dict[str, str] = {
    "ended ok": "ended_ok",
    "ended not ok": "ended_not_ok",
    "executing": "executing",
    "wait condition": "wait_condition",
    "waiting for condition": "wait_condition",
    "wait event": "wait_event",
    "waiting for event": "wait_event",
    "wait user": "wait_user",
    "waiting for user": "wait_user",
    "wait resource": "wait_resource",
    "waiting for resource": "wait_resource",
    "wait host": "wait_host",
    "waiting for host": "wait_host",
    "wait workload": "wait_workload",
    "waiting for workload": "wait_workload",
    "canceled": "canceled",
    "cancelled": "canceled",
}
TERMINAL_STATUSES = {"ended_ok", "ended_not_ok", "canceled"}
WAITING_STATUSES = {"wait_condition", "wait_event", "wait_user", "wait_resource", "wait_host", "wait_workload"}
UP_STATES = {"up", "available", "connected", "active"}

_FINALIZED_RUNS_CACHE_KEY = "finalized_runs_control_m"
_ACTIVE_RUNS_CACHE_KEY = "active_runs_control_m"
_ALERT_TYPE = {"ok": "success", "failed": "error", "canceled": "warning", "unknown": "warning"}


def normalize_status(status: Any) -> str:
    if not status:
        return "unknown"
    return STATUS_NORMALIZATION.get(str(status).strip().lower(), "unknown")


def result_from_status(status: str) -> str:
    # Map the normalized status to a known result after job run completion.
    if status == "ended_ok":
        return "ok"
    if status == "ended_not_ok":
        return "failed"
    if status == "canceled":
        return "canceled"
    return "unknown"


def build_run_key(job: dict[str, Any]) -> str | None:
    job_id = job.get("jobId")
    if not job_id:
        return None

    number_of_runs = job.get("numberOfRuns")
    if number_of_runs is not None:
        return f"{job_id}#{number_of_runs}"

    start_time = timestamp_string(job.get("startTime"))
    if start_time:
        return f"{job_id}#{start_time}"

    end_time = timestamp_string(job.get("endTime"))
    if end_time:
        return f"{job_id}#{end_time}"

    return None


def job_metric_tags(base_tags: list[str], job: dict[str, Any], ctm_server: str | None = None) -> list[str]:
    if ctm_server is None:
        ctm_server = str(job.get("ctm") or job.get("server") or "unknown")
    tags = base_tags + [f"ctm_server:{ctm_server}"]

    job_name = job.get("name")
    if job_name:
        tags.append(f"job_name:{job_name}")

    folder = job.get("folder")
    if folder:
        tags.append(f"folder:{folder}")

    job_type = job.get("type")
    if job_type:
        tags.append(f"type:{str(job_type).lower()}")

    return tags


def duration_ms(job: dict[str, Any]) -> int | None:
    # Calculate the job duration in milliseconds from start/end timestamps.
    start = parse_datetime(job.get("startTime"))
    end = parse_datetime(job.get("endTime"))
    if start is None or end is None:
        return None
    delta = int((end - start).total_seconds() * 1000)
    if delta < 0:
        return None
    return delta


def parse_datetime(value: Any) -> datetime | None:
    # Parse datetime values from compact Control-M format or human-readable fallback.
    raw = timestamp_string(value)
    if not raw:
        return None

    compact = raw.strip()
    if compact.isdigit() and len(compact) == 14:
        try:
            return datetime.strptime(compact, "%Y%m%d%H%M%S")
        except ValueError:
            return None

    try:
        return datetime.strptime(compact, "%b %d, %Y, %I:%M:%S %p")
    except ValueError:
        return None


def timestamp_string(value: Any) -> str | None:
    # Estimated times can sometimes be a list...
    if isinstance(value, list):
        if not value:
            return None
        first = value[0]
        if first is None:
            return None
        return str(first)

    if value is None:
        return None

    return str(value)


def prune_state_map(state_map: dict[str, float], now: float, ttl_seconds: int) -> bool:
    stale = [key for key, seen_at in state_map.items() if now - seen_at > ttl_seconds]
    for key in stale:
        state_map.pop(key)
    return bool(stale)


def _format_timestamp(raw: Any) -> str | None:
    dt = parse_datetime(raw)
    if dt is not None:
        return dt.strftime("%b %d, %Y, %I:%M:%S %p")
    # Unparseable but non-empty — return the raw value so it's still visible.
    s = timestamp_string(raw)
    return s if s else None


def _build_event_text(job: dict[str, Any], result: str, ctm_server: str, job_duration: int | None) -> str:
    lines = [f"Result: {result}", f"Server: {ctm_server}"]

    folder = job.get("folder")
    if folder:
        lines.append(f"Folder: {folder}")

    job_id = job.get("jobId")
    if job_id:
        lines.append(f"Job ID: {job_id}")

    number_of_runs = job.get("numberOfRuns")
    if number_of_runs is not None:
        lines.append(f"Run #: {number_of_runs}")

    start = _format_timestamp(job.get("startTime"))
    if start:
        lines.append(f"Start: {start}")

    end = _format_timestamp(job.get("endTime"))
    if end:
        lines.append(f"End: {end}")

    if job_duration is not None:
        lines.append(f"Duration: {job_duration}ms")

    return "\n".join(lines)


class JobCollector:
    def __init__(self, check: AgentCheck, client: ControlMClient, base_tags: list[str]) -> None:
        self._check = check
        self._client = client
        self._base_tags = base_tags

        instance = check.instance
        self._job_status_limit = int(instance.get("job_status_limit", 10000))
        self._job_name_filter = instance.get("job_name_filter", "*")
        self._finalized_ttl = int(instance.get("finalized_ttl_seconds", 86400))
        self._active_ttl = int(instance.get("active_ttl_seconds", 21600))

        self._emit_job_events = bool(instance.get("emit_job_events", False))
        self._emit_success_events = bool(instance.get("emit_success_events", False))
        raw_threshold = instance.get("slow_run_threshold_ms")
        self._slow_run_threshold_ms: int | None = int(raw_threshold) if raw_threshold is not None else None

        query = {"limit": self._job_status_limit, "jobname": self._job_name_filter}
        self._jobs_status_url = f"{client.api_endpoint}/run/jobs/status?{urlencode(query)}"

        self._finalized_runs: dict[str, float] = {}
        self._active_runs: dict[str, float] = {}
        self._load_runs_cache(_FINALIZED_RUNS_CACHE_KEY, self._finalized_ttl, self._finalized_runs)
        self._load_runs_cache(_ACTIVE_RUNS_CACHE_KEY, self._active_ttl, self._active_runs)

    def collect(self) -> None:
        try:
            response = self._client.request("get", self._jobs_status_url)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            self._check.log.warning("Unable to collect job statuses from /run/jobs/status: %s", e)
            return

        if not isinstance(payload, dict):
            return

        statuses = payload.get("statuses", [])
        total = payload.get("total")
        if total is not None:
            self._check.gauge("jobs.total", total, tags=self._base_tags)
        self._check.gauge("jobs.returned", len(statuses), tags=self._base_tags)

        now = time.time()
        finalized_changed = prune_state_map(self._finalized_runs, now, self._finalized_ttl)
        active_changed = prune_state_map(self._active_runs, now, self._active_ttl)

        if not statuses:
            if finalized_changed:
                self._persist_cache(_FINALIZED_RUNS_CACHE_KEY, self._finalized_runs)
            if active_changed:
                self._persist_cache(_ACTIVE_RUNS_CACHE_KEY, self._active_runs)
            return

        status_counts: dict[tuple[str, str], int] = {}
        active_by_server: dict[str, int] = {}
        waiting_by_server: dict[str, int] = {}

        for job in statuses:
            if not isinstance(job, dict):
                continue

            normalized = normalize_status(job.get("status"))
            ctm_server = str(job.get("ctm") or job.get("server") or "unknown")

            _increment(status_counts, (ctm_server, normalized))
            if normalized not in TERMINAL_STATUSES:
                _increment(active_by_server, ctm_server)
            if normalized in WAITING_STATUSES:
                _increment(waiting_by_server, ctm_server)

            dedupe_key = build_run_key(job)

            if normalized in TERMINAL_STATUSES:
                if self._handle_terminal_job(job, normalized, dedupe_key, now, ctm_server):
                    finalized_changed = True
                if dedupe_key is not None and dedupe_key in self._active_runs:
                    self._active_runs.pop(dedupe_key)
                    active_changed = True
            elif dedupe_key is not None:
                if dedupe_key not in self._active_runs:
                    active_changed = True
                self._active_runs[dedupe_key] = now

        for (ctm_server, normalized), count in status_counts.items():
            tags = self._base_tags + [f"ctm_server:{ctm_server}", f"status:{normalized}"]
            self._check.gauge("jobs.by_status", count, tags=tags)

        for ctm_server, count in active_by_server.items():
            tags = self._base_tags + [f"ctm_server:{ctm_server}"]
            self._check.gauge("jobs.active", count, tags=tags)

        global_waiting = sum(waiting_by_server.values())
        self._check.gauge("jobs.waiting.total", global_waiting, tags=self._base_tags)
        for ctm_server, count in waiting_by_server.items():
            tags = self._base_tags + [f"ctm_server:{ctm_server}"]
            self._check.gauge("jobs.waiting.total", count, tags=tags)

        if finalized_changed:
            self._persist_cache(_FINALIZED_RUNS_CACHE_KEY, self._finalized_runs)
        if active_changed:
            self._persist_cache(_ACTIVE_RUNS_CACHE_KEY, self._active_runs)

    def _handle_terminal_job(
        self, job: dict[str, Any], normalized: str, dedupe_key: str | None, now: float, ctm_server: str
    ) -> bool:
        if dedupe_key is None:
            self._check.log.debug("Skipping completion metrics for job without dedupe key: %s", job.get("name"))
            return False
        if dedupe_key in self._finalized_runs:
            return False

        result = result_from_status(normalized)
        tags = job_metric_tags(self._base_tags, job, ctm_server=ctm_server)
        completion_tags = tags + [f"result:{result}"]
        self._check.count("job.run.count", 1, tags=completion_tags)

        job_duration = duration_ms(job)
        if job_duration is not None:
            self._check.histogram("job.run.duration_ms", job_duration, tags=completion_tags)

        if self._emit_job_events:
            self._emit_job_event(job, result, ctm_server, completion_tags, job_duration)

        self._finalized_runs[dedupe_key] = now
        return True

    def _emit_job_event(
        self,
        job: dict[str, Any],
        result: str,
        ctm_server: str,
        tags: list[str],
        job_duration: int | None,
    ) -> None:
        job_name = job.get("name", "unknown")
        agg_key = f"{ctm_server}:{job_name}"

        if result != "ok" or self._emit_success_events:
            self._check.event(
                {
                    "timestamp": int(time.time()),
                    "event_type": "control_m.job.completion",
                    "msg_title": f"Control-M job {result}: {job_name}",
                    "msg_text": _build_event_text(job, result, ctm_server, job_duration),
                    "alert_type": _ALERT_TYPE.get(result, "info"),
                    "source_type_name": "control_m",
                    "tags": tags,
                    "aggregation_key": agg_key,
                }
            )

        if (
            self._slow_run_threshold_ms is not None
            and job_duration is not None
            and job_duration > self._slow_run_threshold_ms
        ):
            self._check.event(
                {
                    "timestamp": int(time.time()),
                    "event_type": "control_m.job.slow_run",
                    "msg_title": f"Control-M slow run: {job_name} ({job_duration}ms > {self._slow_run_threshold_ms}ms)",
                    "msg_text": _build_event_text(job, result, ctm_server, job_duration),
                    "alert_type": "warning",
                    "source_type_name": "control_m",
                    "tags": tags,
                    "aggregation_key": agg_key,
                }
            )

    def _load_runs_cache(self, cache_key: str, ttl: int, target: dict[str, float]) -> None:
        raw = self._check.read_persistent_cache(cache_key)
        if not raw:
            return
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            self._check.log.warning("Could not decode persistent cache for %s; starting empty", cache_key)
            return
        if not isinstance(data, dict):
            self._check.log.warning("Persistent cache for %s is not a dict; starting empty", cache_key)
            return

        now = time.time()
        for key, value in data.items():
            if not isinstance(key, str):
                continue
            try:
                seen_at = float(value)
            except (TypeError, ValueError):
                continue
            if now - seen_at <= ttl:
                target[key] = seen_at

        self._check.log.debug("Loaded %d entries from persistent cache %s", len(target), cache_key)

    def _persist_cache(self, cache_key: str, state_map: dict[str, float]) -> None:
        try:
            self._check.write_persistent_cache(cache_key, json.dumps(state_map))
        except Exception as e:
            self._check.log.warning("Could not persist cache %s: %s", cache_key, e)


def _increment(counter: dict, key: object) -> None:
    counter[key] = counter.get(key, 0) + 1
