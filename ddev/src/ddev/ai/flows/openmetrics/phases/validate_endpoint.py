# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

import httpx
from prometheus_client import Metric
from prometheus_client.openmetrics.parser import text_string_to_metric_families as parse_openmetrics
from prometheus_client.parser import text_string_to_metric_families as parse_prometheus

from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.phases.config import AgentConfig, FlowConfigError, PhaseConfig

_REQUEST_TIMEOUT_SECONDS = 10.0
_MAX_METRIC_SAMPLES = 10


class EndpointValidationError(Exception):
    """Raised by ValidateEndpointPhase when the target endpoint is unreachable or its body is unusable."""


def _parse_exposition(body: str, content_type: str) -> tuple[list[Metric], str]:
    """Parse body with the parser matching content_type.

    Returns (families, exposition_format) where exposition_format is
    "openmetrics" or "prometheus". Raises EndpointValidationError if parsing
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
        raise EndpointValidationError(f"Body is not valid {exposition_format} exposition: {e}") from e

    if not families:
        raise EndpointValidationError(f"Body parsed as {exposition_format} but contained zero metric families")

    return families, exposition_format


def _build_memory_text(
    url: str,
    status: int,
    content_type: str,
    exposition_format: str,
    families: list[Metric],
) -> str:
    """Render the markdown memory file describing the validated endpoint."""
    lines = [
        "# Endpoint validation",
        "",
        f"- **URL:** {url}",
        f"- **HTTP status:** {status}",
        f"- **Content-Type:** {content_type}",
        f"- **Exposition format:** {exposition_format}",
        f"- **Metric families detected:** {len(families)}",
        f"- **First {min(_MAX_METRIC_SAMPLES, len(families))} metric names:**",
    ]
    for metric in families[:_MAX_METRIC_SAMPLES]:
        if metric.type:
            lines.append(f"  - `{metric.name}` ({metric.type})")
        else:
            lines.append(f"  - `{metric.name}`")
    lines.append("")
    lines.append("Endpoint is reachable and serves a Prometheus/OpenMetrics-compatible body.")
    return "\n".join(lines)


class ValidateEndpointPhase(Phase):
    """Deterministic Phase 0 for the OpenMetrics pipeline.

    Confirms that ``endpoint_url`` (from runtime variables) is reachable and
    serves a body that the same parser used by ``OpenMetricsBaseCheckV2`` can
    accept. Aborts the pipeline with EndpointValidationError on any failure so
    the user doesn't burn tokens generating an integration against a dead or
    malformed endpoint. Writes a memory file summarizing the endpoint for
    downstream phases.
    """

    @classmethod
    def validate_config(
        cls,
        phase_id: str,
        config: PhaseConfig,
        agents: dict[str, AgentConfig],
    ) -> None:
        # This phase is deterministic: no agent, no tasks, no memory prompt.
        # Catching misconfigured flow.yaml entries at orchestrator startup
        # avoids surprising mid-pipeline failures.
        if config.agent is not None:
            raise FlowConfigError(f"Phase {phase_id!r} (ValidateEndpointPhase) must not declare 'agent'")
        if config.tasks:
            raise FlowConfigError(f"Phase {phase_id!r} (ValidateEndpointPhase) must not declare 'tasks'")
        if config.checkpoint is not None:
            raise FlowConfigError(f"Phase {phase_id!r} (ValidateEndpointPhase) must not declare 'checkpoint'")

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        endpoint_url = context.get("endpoint_url")
        if not endpoint_url:
            raise FlowConfigError(f"Phase {self._phase_id!r}: 'endpoint_url' runtime variable is required")

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
                response = await client.get(endpoint_url)
        except httpx.TimeoutException as e:
            raise EndpointValidationError(
                f"Endpoint timed out after {_REQUEST_TIMEOUT_SECONDS}s: {endpoint_url}"
            ) from e
        except httpx.RequestError as e:
            raise EndpointValidationError(f"Request failed for {endpoint_url}: {e}") from e

        if response.status_code != 200:
            raise EndpointValidationError(
                f"Endpoint returned HTTP {response.status_code} (expected 200): {endpoint_url}"
            )

        content_type = response.headers.get("Content-Type", "")
        try:
            families, exposition_format = _parse_exposition(response.text, content_type)
        except EndpointValidationError as e:
            raise EndpointValidationError(f"{e} ({endpoint_url})") from e

        memory_text = _build_memory_text(
            url=endpoint_url,
            status=response.status_code,
            content_type=content_type,
            exposition_format=exposition_format,
            families=families,
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
                "metric_count": len(families),
                "sample_metric_names": [m.name for m in families[:_MAX_METRIC_SAMPLES]],
            },
        )
