# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from pathlib import Path
from typing import Any

import httpx
from prometheus_client import Metric
from prometheus_client.openmetrics.parser import text_string_to_metric_families as parse_openmetrics
from prometheus_client.parser import text_string_to_metric_families as parse_prometheus

from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.phases.config import AgentConfig, FlowConfigError, PhaseConfig

REQUEST_TIMEOUT_SECONDS = 10.0
RESPONSE_BODY_LIMIT_BYTES = 10 * 1024 * 1024  # 10 MB
JSONL_FILENAME_SUFFIX = "_metrics.jsonl"


class EndpointInspectionError(Exception):
    """Raised when the endpoint is unreachable, its body is unusable, or the catalog cannot be written."""


def _parse_exposition(body: str, content_type: str) -> tuple[list[Metric], str]:
    """Parse body with the parser matching content_type.

    Returns (families, exposition_format) where exposition_format is
    "openmetrics" or "prometheus". Raises EndpointInspectionError if parsing
    fails or yields zero metric families.
    """
    if content_type.startswith("application/openmetrics-text"):
        parser = parse_openmetrics
        exposition_format = "openmetrics"
    else:
        parser = parse_prometheus
        exposition_format = "prometheus"

    try:
        families = list(parser(body))
    except Exception as e:
        raise EndpointInspectionError(
            f"Body is not valid {exposition_format} exposition ({type(e).__name__}): {e}"
        ) from e

    if not families:
        raise EndpointInspectionError(f"Body parsed as {exposition_format} but contained zero metric families")

    return families, exposition_format


def _build_jsonl_rows(families: list[Metric]) -> list[dict[str, Any]]:
    """Build one JSONL row per metric family."""
    rows: list[dict[str, Any]] = []
    for metric in families:
        label_keys: set[str] = set()
        for sample in metric.samples:
            label_keys.update(sample.labels.keys())
        rows.append(
            {
                "name": metric.name,
                "type": metric.type,
                "help": metric.documentation or "",
                "unit": metric.unit or "",
                "label_keys": sorted(label_keys),
                "sample_count": len(metric.samples),
            }
        )
    return rows


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically write rows as JSON Lines to path."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                try:
                    line = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
                except (TypeError, ValueError) as e:
                    raise EndpointInspectionError(f"Failed to serialize metric {row.get('name')!r}: {e}") from e
                fh.write(line)
                fh.write("\n")
        os.replace(tmp_path, path)
    except EndpointInspectionError:
        _remove_if_exists(tmp_path)
        raise
    except OSError as e:
        _remove_if_exists(tmp_path)
        raise EndpointInspectionError(f"Failed to write metrics catalog at {path}: {e}") from e


def _build_memory_text(
    url: str,
    status: int,
    content_type: str,
    exposition_format: str,
    metric_count: int,
    jsonl_path: Path,
) -> str:
    """Render the markdown memory file describing the inspected endpoint."""
    lines = [
        "# Endpoint inspection",
        "",
        f"- **URL:** {url}",
        f"- **HTTP status:** {status}",
        f"- **Content-Type:** {content_type}",
        f"- **Exposition format:** {exposition_format}",
        f"- **Metric families detected:** {metric_count}",
        f"- **Metrics catalog:** {jsonl_path}",
        "",
        "Endpoint is reachable and serves a Prometheus/OpenMetrics-compatible body.",
        "The full list of metrics with metadata is in the catalog file above.",
    ]
    return "\n".join(lines)


class InspectEndpointPhase(Phase):
    """Deterministic Phase 0 for the OpenMetrics pipeline.

    Performs a single HTTP fetch of ``endpoint_url`` and:

    1. Confirms the endpoint is reachable (HTTP 200).
    2. Confirms the body is valid Prometheus or OpenMetrics exposition.
    3. Writes a ``<phase_id>_metrics.jsonl`` sidecar next to the memory file,
       with one row per metric family — the ground-truth catalog later phases
       use to drive metric renaming, ``metrics.py`` mapping, and
       ``metadata.csv`` generation.

    Aborts the pipeline with EndpointInspectionError on any failure.
    """

    @classmethod
    def validate_config(
        cls,
        phase_id: str,
        config: PhaseConfig,
        agents: dict[str, AgentConfig],
    ) -> None:
        if config.agent is not None:
            raise FlowConfigError(f"Phase {phase_id!r} (InspectEndpointPhase) must not declare 'agent'")
        if config.tasks:
            raise FlowConfigError(f"Phase {phase_id!r} (InspectEndpointPhase) must not declare 'tasks'")
        if config.checkpoint is not None:
            raise FlowConfigError(f"Phase {phase_id!r} (InspectEndpointPhase) must not declare 'checkpoint'")

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        endpoint_url = context.get("endpoint_url")
        if not endpoint_url:
            raise FlowConfigError(f"Phase {self._phase_id!r}: 'endpoint_url' runtime variable is required")

        limit_mb = RESPONSE_BODY_LIMIT_BYTES // (1024 * 1024)
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                async with client.stream("GET", endpoint_url) as response:
                    if response.status_code != 200:
                        raise EndpointInspectionError(
                            f"Endpoint returned HTTP {response.status_code} (expected 200): {endpoint_url}"
                        )
                    chunks: list[bytes] = []
                    received = 0
                    async for chunk in response.aiter_bytes():
                        received += len(chunk)
                        if received > RESPONSE_BODY_LIMIT_BYTES:
                            raise EndpointInspectionError(f"Response body exceeds {limit_mb} MB limit: {endpoint_url}")
                        chunks.append(chunk)
                    body = b"".join(chunks).decode("utf-8", errors="replace")
                    content_type = response.headers.get("Content-Type", "")
        except EndpointInspectionError:
            raise
        except httpx.TimeoutException as e:
            raise EndpointInspectionError(f"Endpoint timed out after {REQUEST_TIMEOUT_SECONDS}s: {endpoint_url}") from e
        except httpx.RequestError as e:
            raise EndpointInspectionError(f"Request failed for {endpoint_url}: {e}") from e

        try:
            families, exposition_format = _parse_exposition(body, content_type)
        except EndpointInspectionError as e:
            raise EndpointInspectionError(f"{e} ({endpoint_url})") from e

        rows = _build_jsonl_rows(families)
        self._checkpoint_manager.memory_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = (self._checkpoint_manager.memory_dir / f"{self._phase_id}{JSONL_FILENAME_SUFFIX}").resolve()
        _write_jsonl(jsonl_path, rows)

        metric_count = len(families)
        memory_text = _build_memory_text(
            url=endpoint_url,
            status=response.status_code,
            content_type=content_type,
            exposition_format=exposition_format,
            metric_count=metric_count,
            jsonl_path=jsonl_path,
        )

        return PhaseOutcome(
            memory_text=memory_text,
            total_input_tokens=0,
            total_output_tokens=0,
            extra_checkpoint={
                "endpoint_url": endpoint_url,
                "status_code": response.status_code,
                "content_type": content_type,
                "exposition_format": exposition_format,
                "metric_count": metric_count,
                "metrics_jsonl_path": str(jsonl_path),
            },
        )
