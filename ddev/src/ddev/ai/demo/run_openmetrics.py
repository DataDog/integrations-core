#!/usr/bin/env python
"""Demo: run the OpenMetrics AI flow with mocked agents.

Usage (from the integrations-core repo root, using the ddev venv):

    python -m ddev.ai.demo.run_openmetrics

Or with custom values:

    python -m ddev.ai.demo.run_openmetrics --integration nginx --endpoint http://localhost:9113/metrics

Output goes to a temporary directory printed at the end. Inspect checkpoints.yaml
and the *_memory.md files to see what each phase produced.
"""

import argparse
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolResultMessage
from ddev.ai.react.callbacks import CallbackSet
from ddev.ai.tools.core.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Mock agent
# ---------------------------------------------------------------------------


class MockAgent:
    """Replays scripted responses. One instance per phase."""

    def __init__(self, phase_id: str, responses: list[AgentResponse]) -> None:
        self._phase_id = phase_id
        self._responses = list(responses)
        self._index = 0
        self.name = phase_id
        self._history: list[Any] = []

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        response = self._responses[self._index]
        self._index += 1
        return response

    def reset(self) -> None:
        self._history = []

    async def compact(self) -> AgentResponse | None:
        return None

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        return None


def _make_response(text: str, input_tokens: int = 500, output_tokens: int = 200) -> AgentResponse:
    return AgentResponse(
        stop_reason=StopReason.END_TURN,
        text=text,
        tool_calls=[],
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            context_usage=ContextUsage(window_size=200_000, used_tokens=input_tokens + output_tokens),
        ),
    )


# ---------------------------------------------------------------------------
# Scripted responses — one list per phase
# Each phase needs: 1 response per task + 1 response for the memory step
# ---------------------------------------------------------------------------

PHASE_RESPONSES: dict[str, list[AgentResponse]] = {
    # Phase 0: validate_endpoint — 1 task + 1 memory = 2 responses
    "validate_endpoint": [
        _make_response(
            "Endpoint validation complete.\n\n"
            "- Endpoint http://localhost:9113/metrics is reachable (HTTP 200)\n"
            "- Response contains valid OpenMetrics format with HELP, TYPE, and metric lines\n"
            "- Found 47 metric families including nginx_connections_active, nginx_http_requests_total, etc.\n"
            "- Content-Type: text/plain; version=0.0.4\n\n"
            "The endpoint is valid and ready for metrics collection."
        ),
        _make_response(
            "Validated endpoint: http://localhost:9113/metrics\n"
            "Integration: nginx\n"
            "Metrics format: OpenMetrics (text/plain; version=0.0.4)\n"
            "Metric families found: 47\n"
            "Status: endpoint reachable and valid"
        ),
    ],
    # Phase 1: collect_metrics — 2 tasks + 1 memory = 3 responses
    "collect_metrics": [
        _make_response(
            "Generated temporary check code.\n\n"
            "Created `nginx/datadog_checks/nginx/check.py` with OpenMetricsBaseCheckV2.\n"
            "The check collects all metrics from the /metrics endpoint and writes them\n"
            "to a JSONL file at `nginx/collected_metrics.jsonl`.\n"
            "Also generated `nginx/assets/configuration/spec.yaml` with the endpoint config.",
            input_tokens=800,
            output_tokens=400,
        ),
        _make_response(
            "Collected 47 metrics from the endpoint. JSONL file written.\n\n"
            "Sample metrics:\n"
            '  {"name": "nginx_connections_active", "type": "gauge", "labels": []}\n'
            '  {"name": "nginx_connections_reading", "type": "gauge", "labels": []}\n'
            '  {"name": "nginx_connections_writing", "type": "gauge", "labels": []}\n'
            '  {"name": "nginx_connections_waiting", "type": "gauge", "labels": []}\n'
            '  {"name": "nginx_http_requests_total", "type": "counter", "labels": ["method", "status"]}\n'
            "  ... (42 more metrics)\n\n"
            "All metrics saved to nginx/collected_metrics.jsonl",
            input_tokens=600,
            output_tokens=300,
        ),
        _make_response(
            "Collected 47 metrics from http://localhost:9113/metrics.\n"
            "JSONL file: nginx/collected_metrics.jsonl\n"
            "Config files: nginx/assets/configuration/spec.yaml, nginx/datadog_checks/nginx/check.py\n"
            "Key metrics: nginx_connections_active, nginx_http_requests_total, nginx_up"
        ),
    ],
    # Phase 2: rename_metrics — 1 task + 1 memory = 2 responses
    "rename_metrics": [
        _make_response(
            "Renamed all 47 metrics following Datadog conventions.\n\n"
            "Key mappings:\n"
            "  nginx_connections_active     -> nginx.connections.active\n"
            "  nginx_connections_reading    -> nginx.connections.reading\n"
            "  nginx_connections_writing    -> nginx.connections.writing\n"
            "  nginx_connections_waiting    -> nginx.connections.waiting\n"
            "  nginx_http_requests_total    -> nginx.http.requests.total (count)\n"
            "  nginx_up                     -> nginx.up (gauge)\n\n"
            "Generated:\n"
            "  - nginx/metadata.csv (47 entries)\n"
            "  - nginx/assets/configuration/metrics.yaml (47 mappings)",
            input_tokens=1200,
            output_tokens=600,
        ),
        _make_response(
            "Renamed 47 metrics to Datadog format.\n"
            "metrics.yaml: nginx/assets/configuration/metrics.yaml\n"
            "metadata.csv: nginx/metadata.csv\n"
            "Pattern: nginx_{category}_{name} -> nginx.{category}.{name}"
        ),
    ],
    # Phase 3: generate_tests — 1 task + 1 memory = 2 responses
    "generate_tests": [
        _make_response(
            "Generated test suite for the nginx integration.\n\n"
            "Created files:\n"
            "  - nginx/tests/test_check.py (unit tests, 12 test cases)\n"
            "  - nginx/tests/test_integration.py (integration tests, 5 test cases)\n"
            "  - nginx/tests/conftest.py (fixtures and mock data)\n\n"
            "Tests cover:\n"
            "  - Metric collection from live endpoint\n"
            "  - All 47 metric mappings validated against metadata.csv\n"
            "  - Connection error handling\n"
            "  - Configuration validation\n\n"
            "All 17 tests passing.",
            input_tokens=1000,
            output_tokens=500,
        ),
        _make_response(
            "Test files: test_check.py (12 tests), test_integration.py (5 tests), conftest.py\n"
            "All 17 tests passing.\n"
            "Coverage: metric collection, metadata validation, error handling, config validation"
        ),
    ],
    # Phase 4: write_docs — 1 task + 1 memory = 2 responses
    "write_docs": [
        _make_response(
            "Generated README.md for the nginx integration.\n\n"
            "Sections:\n"
            "  1. Overview — what the integration monitors\n"
            "  2. Setup — installation and configuration\n"
            "  3. Data Collected — all 47 metrics with descriptions\n"
            "  4. Troubleshooting — common issues and solutions\n\n"
            "Written to nginx/README.md following Datadog documentation standards.",
            input_tokens=800,
            output_tokens=400,
        ),
        _make_response(
            "README.md written to nginx/README.md.\n"
            "Covers: overview, setup, 47 metrics documented, troubleshooting section."
        ),
    ],
}


# ---------------------------------------------------------------------------
# Patching
# ---------------------------------------------------------------------------


def _patch(integration_name: str) -> tuple[Any, Any]:
    """Patch AnthropicAgent and ToolRegistry.from_names. Returns originals for restore."""
    import ddev.ai.phases.base as base_module

    original_agent = base_module.AnthropicAgent
    original_from_names = ToolRegistry.from_names

    def mock_factory(**kwargs: Any) -> MockAgent:
        phase_id = kwargs["name"]
        print(f"  [{phase_id}] Agent created (model={kwargs.get('model', 'default')})")
        return MockAgent(phase_id, PHASE_RESPONSES[phase_id])

    base_module.AnthropicAgent = mock_factory  # type: ignore[misc, assignment]
    ToolRegistry.from_names = classmethod(lambda cls, names: ToolRegistry([]))  # type: ignore[method-assign, assignment]

    # Inject integration_name into the scripted responses where useful
    for phase_id, responses in PHASE_RESPONSES.items():
        for i, r in enumerate(responses):
            if "nginx" in r.text and integration_name != "nginx":
                PHASE_RESPONSES[phase_id][i] = _make_response(
                    r.text.replace("nginx", integration_name),
                    r.usage.input_tokens,
                    r.usage.output_tokens,
                )

    return original_agent, original_from_names


def _restore(originals: tuple[Any, Any]) -> None:
    import ddev.ai.phases.base as base_module

    base_module.AnthropicAgent = originals[0]  # type: ignore[misc, assignment]
    ToolRegistry.from_names = originals[1]  # type: ignore[method-assign, assignment]


# ---------------------------------------------------------------------------
# Callbacks for live progress
# ---------------------------------------------------------------------------


def _make_progress_callbacks() -> CallbackSet:
    cb = CallbackSet()

    @cb.on_agent_response
    async def on_response(response: AgentResponse, iteration: int) -> None:
        # Print first 80 chars of the response
        preview = response.text[:80].replace("\n", " ")
        if len(response.text) > 80:
            preview += "..."
        print(f"    Agent response (iter {iteration}): {preview}")

    @cb.on_complete
    async def on_complete(result: Any) -> None:
        print(
            f"    Task complete ({result.iterations} iters, {result.total_input_tokens}"
            "in / {result.total_output_tokens} out)"
        )

    return cb


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo: OpenMetrics AI flow with mocked agents")
    parser.add_argument("--integration", default="nginx", help="Integration name (default: nginx)")
    parser.add_argument("--endpoint", default="http://localhost:9113/metrics", help="Endpoint URL")
    parser.add_argument("--output", default=None, help="Output directory (default: temp dir)")
    args = parser.parse_args()

    flow_dir = Path(__file__).parent / "openmetrics"
    output_dir = Path(args.output) if args.output else Path(tempfile.mkdtemp(prefix="openmetrics_demo_"))

    print(f"{'=' * 60}")
    print("  OpenMetrics AI Flow Demo (mocked agents)")
    print(f"  Integration: {args.integration}")
    print(f"  Endpoint:    {args.endpoint}")
    print(f"  Output:      {output_dir}")
    print(f"{'=' * 60}\n")

    originals = _patch(args.integration)
    try:
        from ddev.ai.phases.orchestrator import PhaseOrchestrator

        callbacks = _make_progress_callbacks()
        orchestrator = PhaseOrchestrator(
            flow_yaml_path=flow_dir / "flow.yaml",
            checkpoint_path=output_dir / "checkpoints.yaml",
            runtime_variables={
                "integration_name": args.integration,
                "endpoint_url": args.endpoint,
            },
            anthropic_client=MagicMock(),
            callback_sets=[callbacks],
            grace_period=1,
        )

        print("Starting orchestrator...\n")
        orchestrator.run()
        print("\nOrchestrator finished.\n")

    finally:
        _restore(originals)

    # Print results
    print(f"{'=' * 60}")
    print("  Results")
    print(f"{'=' * 60}\n")

    checkpoints_file = output_dir / "checkpoints.yaml"
    if checkpoints_file.exists():
        print("--- checkpoints.yaml ---")
        print(checkpoints_file.read_text())

    for memory_file in sorted(output_dir.glob("*_memory.md")):
        print(f"--- {memory_file.name} ---")
        print(memory_file.read_text())
        print()

    print(f"All output in: {output_dir}")


if __name__ == "__main__":
    main()
