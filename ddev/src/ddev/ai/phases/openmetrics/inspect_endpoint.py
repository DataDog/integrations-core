# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import httpx
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, model_validator

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import PhaseConfig
from ddev.ai.phases.base import Phase, PhaseOutcome

if TYPE_CHECKING:
    from prometheus_client import Metric

REQUEST_TIMEOUT_SECONDS = 10.0
RESPONSE_BODY_LIMIT_BYTES = 10 * 1024 * 1024  # 10 MB
# Mirror the Accept header the OpenMetrics V2 scraper sends by default (use_latest_spec=False):
# `text/plain`. Without an explicit Accept, a server that supports both formats may volunteer
# `application/openmetrics-text` here while serving Prometheus `text/plain` to the generated
# check — so the catalog we build (and metrics.yaml) could disagree with what the check actually
# scrapes (counter `_total` naming, metric typing). Inspecting in the same format the check will
# scrape keeps the two consistent.
DEFAULT_ACCEPT_HEADER = "text/plain"
JSONL_FILENAME_SUFFIX = "_metrics.jsonl"
EXPOSITION_FILENAME_SUFFIX = "_exposition.txt"


class EndpointInspectionError(Exception):
    """Raised when the endpoint is unreachable, its body is unusable, or the catalog cannot be written."""


def normalize_endpoint_name(v: str) -> str:
    """snake_case an endpoint name and reject anything that isn't a valid identifier."""
    name = re.sub(r"[^a-z0-9]+", "_", v.strip().lower()).strip("_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError(f"endpoint name {v!r} is not a valid identifier after normalization")
    return name


def requires_http_scheme(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return url


class EndpointSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, AfterValidator(normalize_endpoint_name)]
    url: Annotated[str, Field(min_length=1), AfterValidator(requires_http_scheme)]


class InspectInput(BaseModel):
    """InspectEndpointPhase's structured input contract."""

    model_config = ConfigDict(extra="forbid")
    endpoints: list[EndpointSpec]

    @model_validator(mode="after")
    def _non_empty_unique(self) -> InspectInput:
        names = [e.name for e in self.endpoints]
        if not names:
            raise ValueError("at least one endpoint is required")
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise ValueError(f"duplicate endpoint names after normalization: {dupes}")
        return self


@dataclass(frozen=True)
class EndpointResult:
    name: str
    url: str
    status_code: int
    content_type: str
    exposition_format: str
    metric_count: int
    metrics_jsonl_path: str  # absolute path, as strpat
    exposition_path: str  # absolute path, as str


def _parse_exposition(body: str, content_type: str) -> tuple[list[Metric], str]:
    """Parse body with the parser matching content_type.

    Returns (families, exposition_format) where exposition_format is
    "openmetrics" or "prometheus". Raises EndpointInspectionError if parsing
    fails or yields zero metric families.
    """
    try:
        from prometheus_client.openmetrics.parser import text_string_to_metric_families as parse_openmetrics
        from prometheus_client.parser import text_string_to_metric_families as parse_prometheus
    except ModuleNotFoundError as e:
        raise ConfigError(
            "InspectEndpointPhase requires the 'ai' extra (prometheus-client); install with `pip install ddev[ai]`"
        ) from e

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


def _write_exposition(path: Path, body: str) -> None:
    """Atomically write the verbatim endpoint body, for reuse as a test fixture."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(body, encoding="utf-8")
        os.replace(tmp_path, path)
    except OSError as e:
        _remove_if_exists(tmp_path)
        raise EndpointInspectionError(f"Failed to write exposition snapshot at {path}: {e}") from e


def _fixture_name(name: str, single: bool) -> str:
    """Intended fixture name for an endpoint (single endpoint → generic metrics.txt)."""
    return "tests/fixtures/metrics.txt" if single else f"tests/fixtures/{name}_metrics.txt"


def _build_memory_text(results: list[EndpointResult]) -> str:
    """Render the markdown memory file describing every inspected endpoint."""
    single = len(results) == 1
    lines = [
        "# Endpoint inspection",
        "",
        f"Inspected {len(results)} endpoint(s). Each is reachable and serves a Prometheus/OpenMetrics-compatible body.",
        "",
        "| Endpoint | Format | Metric families |",
        "| --- | --- | --- |",
    ]
    for r in results:
        lines.append(f"| {r.name} | {r.exposition_format} | {r.metric_count} |")
    lines.append("")

    for r in results:
        lines.extend(
            [
                f"## {r.name}",
                "",
                f"- **URL:** {r.url}",
                f"- **HTTP status:** {r.status_code}",
                f"- **Content-Type:** {r.content_type}",
                f"- **Exposition format:** {r.exposition_format}",
                f"- **Metric families detected:** {r.metric_count}",
                f"- **Metrics catalog:** {r.metrics_jsonl_path}",
                f"- **Raw exposition snapshot:** {r.exposition_path}",
                f"- **Intended fixture:** {_fixture_name(r.name, single)}",
                "",
                "The catalog file lists every metric with its metadata. The raw exposition snapshot is the",
                "verbatim endpoint body, suitable for use as a test fixture.",
                "",
            ]
        )
    return "\n".join(lines).rstrip("\n")


async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[str, str, int]:
    """Fetch url, enforce 200 + size limit, return (body, content_type, status_code)."""
    try:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise EndpointInspectionError(f"Endpoint returned HTTP {response.status_code} (expected 200): {url}")
            chunks: list[bytes] = []
            received = 0
            async for chunk in response.aiter_bytes():
                received += len(chunk)
                if received > RESPONSE_BODY_LIMIT_BYTES:
                    limit_mb = RESPONSE_BODY_LIMIT_BYTES // (1024 * 1024)
                    raise EndpointInspectionError(f"Response body exceeds {limit_mb} MB limit: {url}")
                chunks.append(chunk)
            body = b"".join(chunks).decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
    except httpx.TimeoutException as e:
        raise EndpointInspectionError(f"Endpoint timed out after {REQUEST_TIMEOUT_SECONDS}s: {url}") from e
    except httpx.RequestError as e:
        raise EndpointInspectionError(f"Request failed for {url}: {e}") from e

    return body, content_type, response.status_code


def _jsonl_sidecar_path(memory_dir: Path, phase_id: str, name: str) -> Path:
    return (memory_dir / f"{phase_id}_{name}{JSONL_FILENAME_SUFFIX}").resolve()


def _exposition_sidecar_path(memory_dir: Path, phase_id: str, name: str) -> Path:
    return (memory_dir / f"{phase_id}_{name}{EXPOSITION_FILENAME_SUFFIX}").resolve()


async def _inspect_one(
    client: httpx.AsyncClient,
    endpoint: EndpointSpec,
    memory_dir: Path,
    phase_id: str,
) -> EndpointResult:
    """Fetch, parse, and write the sidecars for a single named endpoint."""
    name, url = endpoint.name, endpoint.url
    try:
        body, content_type, status_code = await _fetch(client, url)
    except EndpointInspectionError as e:
        raise EndpointInspectionError(f"[{name}] {e}") from e

    try:
        families, exposition_format = _parse_exposition(body, content_type)
    except EndpointInspectionError as e:
        raise EndpointInspectionError(f"[{name}] {e} ({url})") from e

    header = {
        "endpoint_name": name,
        "endpoint_url": url,
        "exposition_format": exposition_format,
        "metric_families": len(families),
    }
    rows = _build_jsonl_rows(families)

    jsonl_path = _jsonl_sidecar_path(memory_dir, phase_id, name)
    _write_jsonl(jsonl_path, [header, *rows])

    exposition_path = _exposition_sidecar_path(memory_dir, phase_id, name)
    _write_exposition(exposition_path, body)

    return EndpointResult(
        name=name,
        url=url,
        status_code=status_code,
        content_type=content_type,
        exposition_format=exposition_format,
        metric_count=len(families),
        metrics_jsonl_path=str(jsonl_path),
        exposition_path=str(exposition_path),
    )


class InspectEndpointPhase(Phase):
    """Deterministic Phase 0 for the OpenMetrics pipeline.

    Fetches every named endpoint in ``endpoints`` concurrently and, per endpoint:

    1. Confirms the endpoint is reachable (HTTP 200).
    2. Confirms the body is valid Prometheus or OpenMetrics exposition.
    3. Writes a ``<phase_id>_<name>_metrics.jsonl`` sidecar (provenance header line 1 +
       one row per metric family) next to the memory file — the ground-truth catalog
       later phases use to drive metric renaming, ``metrics.py`` mapping, and
       ``metadata.csv`` generation.
    4. Writes a ``<phase_id>_<name>_exposition.txt`` verbatim snapshot for reuse as a fixture.

    All-or-nothing: if any endpoint fails, the phase aborts with a single
    EndpointInspectionError listing every failed endpoint, and any sidecar files
    already written by endpoints that succeeded before a sibling failure are
    deleted so no partial output is left behind.
    """

    @classmethod
    def validate_config(cls, phase_id: str, config: PhaseConfig) -> None:
        if config.agent is not None:
            raise ConfigError(f"Phase {phase_id!r} (InspectEndpointPhase) must not declare 'agent'")
        if config.tasks:
            raise ConfigError(f"Phase {phase_id!r} (InspectEndpointPhase) must not declare 'tasks'")
        if config.checkpoint is not None:
            raise ConfigError(f"Phase {phase_id!r} (InspectEndpointPhase) must not declare 'checkpoint'")

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        raw = context.get("endpoints")
        if raw is None:
            raise ConfigError("'endpoints' runtime variable is required")
        try:
            endpoints = InspectInput.model_validate({"endpoints": raw}).endpoints
        except ValidationError as e:
            raise ConfigError(f"invalid 'endpoints': {e}") from e

        memory_dir = self._checkpoint_manager.memory_dir
        memory_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"Accept": DEFAULT_ACCEPT_HEADER},
        ) as client:
            settled = await asyncio.gather(
                *(_inspect_one(client, ep, memory_dir, self._phase_id) for ep in endpoints),
                return_exceptions=True,
            )

        failures = [(ep.name, r) for ep, r in zip(endpoints, settled, strict=True) if isinstance(r, BaseException)]
        if failures:
            for ep in endpoints:
                _jsonl_sidecar_path(memory_dir, self._phase_id, ep.name).unlink(missing_ok=True)
                _exposition_sidecar_path(memory_dir, self._phase_id, ep.name).unlink(missing_ok=True)
            detail = "; ".join(f"{name}: {err}" for name, err in failures)
            raise EndpointInspectionError(f"{len(failures)} endpoint(s) failed to inspect — {detail}")

        results = [r for r in settled if isinstance(r, EndpointResult)]
        return PhaseOutcome(
            memory_text=_build_memory_text(results),
            total_input_tokens=0,
            total_output_tokens=0,
            checkpoint_data={"endpoints": [asdict(r) for r in results]},
        )
