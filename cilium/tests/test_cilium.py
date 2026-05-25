# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev.replay.adapters.requests import (
    build_get_record,
    install_recording_session_get,
    install_replay_session_get,
)
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    ADDL_GC_OPERATOR_METRICS,
    ADDL_OPERATOR_METRICS,
    AGENT_V1_METRICS,
    AGENT_V1_METRICS_1_14,
    AGENT_V1_METRICS_EXCLUDE_METADATA_CHECK,
    AGENT_V2_METRICS,
    AGENT_V2_METRICS_1_14,
    OPERATOR_V2_METRICS,
    OPERATOR_V2_METRICS_1_14,
    requires_new_environment,
)

pytestmark = [requires_new_environment, pytest.mark.unit]


def _fixture_text(name: str) -> str:
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", name)
    with open(fixture_path) as f:
        return f.read()


@pytest.mark.parametrize("use_openmetrics", [True, False])
def test_agent_check(aggregator, agent_instance_use_openmetrics, mock_agent_data, dd_run_check, check, use_openmetrics):
    c = check(agent_instance_use_openmetrics(use_openmetrics))
    dd_run_check(c)
    for m in AGENT_V2_METRICS + AGENT_V2_METRICS_1_14 if use_openmetrics else AGENT_V1_METRICS + AGENT_V1_METRICS_1_14:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(), exclude=None if use_openmetrics else AGENT_V1_METRICS_EXCLUDE_METADATA_CHECK
    )


def test_agent_check_records_http_fixture(
    monkeypatch, tmp_path, agent_instance_use_openmetrics, dd_run_check, check
) -> None:
    instance = agent_instance_use_openmetrics(True)
    body = _fixture_text("agent_metrics.txt")
    record_path = tmp_path / "cilium-agent-http-recording.json"

    install_recording_session_get(
        monkeypatch, record_path, {instance["agent_endpoint"]: build_get_record(instance["agent_endpoint"], body)}
    )

    dd_run_check(check(instance))

    records = json.loads(record_path.read_text())
    assert len(records) == 1
    record = records[0]
    assert record["method"] == "GET"
    assert record["url"] == instance["agent_endpoint"]
    assert record["status"] == 200
    assert record["headers"] == {"Content-Type": "text/plain"}
    assert record["body"] == body


def test_agent_check_replays_http_fixture(
    monkeypatch, tmp_path, agent_instance_use_openmetrics, dd_run_check, check
) -> None:
    instance = agent_instance_use_openmetrics(True)
    record = build_get_record(instance["agent_endpoint"], _fixture_text("agent_metrics.txt"))
    record_path = tmp_path / "cilium-agent-http-recording.json"
    record_path.write_text(json.dumps([record], indent=2, sort_keys=True) + "\n")

    replayed = install_replay_session_get(monkeypatch, record_path)

    dd_run_check(check(instance))

    assert replayed == [record]


def test_agent_check_replay_metrics_match_fixture(
    monkeypatch, tmp_path, aggregator, agent_instance_use_openmetrics, dd_run_check, check
) -> None:
    instance = agent_instance_use_openmetrics(True)
    record_path = tmp_path / "cilium-agent-http-recording.json"
    install_recording_session_get(
        monkeypatch,
        record_path,
        {instance["agent_endpoint"]: build_get_record(instance["agent_endpoint"], _fixture_text("agent_metrics.txt"))},
    )

    dd_run_check(check(instance))
    aggregator.assert_metric("cilium.endpoint.count")
    aggregator.reset()

    install_replay_session_get(monkeypatch, record_path)
    dd_run_check(check(instance))

    for m in AGENT_V2_METRICS + AGENT_V2_METRICS_1_14:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_operator_check(aggregator, operator_instance_use_openmetrics, mock_operator_data, dd_run_check, check):
    c = check(operator_instance_use_openmetrics(True))

    dd_run_check(c)
    for m in OPERATOR_V2_METRICS + ADDL_OPERATOR_METRICS + ADDL_GC_OPERATOR_METRICS + OPERATOR_V2_METRICS_1_14:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
