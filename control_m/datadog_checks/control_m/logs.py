# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck
    from datadog_checks.control_m.client import ControlMClient

_LOG_LINE_RE = re.compile(r"(\d{2}:\d{2}:\d{2}\s+\d{1,2}-\w{3}-\d{4})\s{2,}(.+)")


def parse_job_log(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("Event Time"):
            continue

        parts = line.split("\t")
        code = parts[-1].strip() if len(parts) > 1 else ""
        body = parts[0] if len(parts) > 1 else line

        match = _LOG_LINE_RE.match(body)
        if match:
            entries.append(
                {
                    "event_time": match.group(1).strip(),
                    "message": match.group(2).strip(),
                    "code": code,
                }
            )
        else:
            entries.append(
                {
                    "event_time": "",
                    "message": body.strip(),
                    "code": code,
                }
            )

    return entries


class LogShipper:
    def __init__(self, check: AgentCheck, client: ControlMClient) -> None:
        self._check = check
        self._client = client

        instance = check.instance
        self._collect_job_logs = str(instance.get("collect_job_logs", "off")).lower()
        self._collect_job_output = bool(instance.get("collect_job_output", False))
        self._max_output_bytes = int(instance.get("max_output_bytes", 32768))

    @property
    def enabled(self) -> bool:
        return self._collect_job_logs in ("failed", "all")

    def ship(
        self,
        job: dict[str, Any],
        result: str,
        ctm_server: str,
        tags: list[str],
    ) -> None:
        if not self._should_collect(result):
            return

        job_id = job.get("jobId")
        if not job_id:
            return

        # Skip folder-type jobs — their logs duplicate child job state transitions.
        if str(job.get("type", "")).lower() == "folder":
            return

        job_name = job.get("name", "unknown")
        folder = job.get("folder", "")
        number_of_runs = job.get("numberOfRuns")
        base_attrs = {
            "job_id": job_id,
            "job_name": job_name,
            "folder": folder,
            "ctm_server": ctm_server,
            "result": result,
            "ddtags": ",".join(tags),
        }
        if number_of_runs is not None:
            base_attrs["number_of_runs"] = str(number_of_runs)

        self._ship_event_log(job_id, base_attrs)

        if self._collect_job_output and result != "ok":
            self._ship_output(job_id, job_name, base_attrs)

    def _should_collect(self, result: str) -> bool:
        if self._collect_job_logs == "all":
            return True
        if self._collect_job_logs == "failed":
            return result != "ok"
        return False

    def _ship_event_log(self, job_id: str, base_attrs: dict[str, Any]) -> None:
        text = self._fetch_text(f"{self._client.api_endpoint}/run/job/{job_id}/log")
        if text is None:
            return

        entries = parse_job_log(text)
        if not entries:
            return

        now = time.time()
        for entry in entries:
            data: dict[str, Any] = {**base_attrs, "timestamp": now}
            data["message"] = entry["message"]
            if entry["event_time"]:
                data["event_time"] = entry["event_time"]
            if entry["code"]:
                data["event_code"] = entry["code"]
            self._check.send_log(data)

    def _ship_output(self, job_id: str, job_name: str, base_attrs: dict[str, Any]) -> None:
        text = self._fetch_text(f"{self._client.api_endpoint}/run/job/{job_id}/output")
        if text is None:
            return

        output = text.replace("\r\n", "\n").strip()
        if not output:
            return

        if len(output) > self._max_output_bytes:
            output = output[: self._max_output_bytes] + "\n... [truncated]"

        data: dict[str, Any] = {
            **base_attrs,
            "timestamp": time.time(),
            "message": output,
            "log_type": "job_output",
        }
        self._check.send_log(data)

    def _fetch_text(self, url: str) -> str | None:
        try:
            response = self._client.request("get", url)
            if not response.ok:
                self._check.log.debug("Log fetch returned HTTP %s for %s", response.status_code, url)
                return None
            return response.text
        except Exception as e:
            self._check.log.debug("Could not fetch log from %s: %s", url, e)
            return None
