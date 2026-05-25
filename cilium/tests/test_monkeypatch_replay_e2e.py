# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from datadog_checks.cilium import CiliumCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import AGENT_V2_METRICS, OPERATOR_V2_PROCESS_METRICS, OPTIONAL_METRICS, requires_new_environment
from .monkeypatch_replay import install_live_recording_session_get, install_replay_session_get

pytestmark = [requires_new_environment, pytest.mark.e2e]


@pytest.fixture
def cilium_instances(dd_environment, dd_get_state):
    return dd_environment or dd_get_state('cilium_instances')


def _run_cilium_check(cilium_instances, dd_run_check):
    for instance in cilium_instances['instances']:
        check = CiliumCheck('cilium', {}, [instance])
        dd_run_check(check)


def _assert_e2e_metrics(aggregator):
    for metric in AGENT_V2_METRICS + OPERATOR_V2_PROCESS_METRICS:
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric, at_least=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_live_cilium_check_records_and_replays_http_fixture(
    monkeypatch, tmp_path, aggregator, cilium_instances, dd_run_check
):
    record_path = tmp_path / 'cilium-live-http-recording.json'

    recorded = install_live_recording_session_get(monkeypatch, record_path)
    _run_cilium_check(cilium_instances, dd_run_check)
    _assert_e2e_metrics(aggregator)

    records = json.loads(record_path.read_text())
    assert records == recorded
    assert {record['url'] for record in records} == {
        instance['agent_endpoint'] for instance in cilium_instances['instances'] if 'agent_endpoint' in instance
    } | {instance['operator_endpoint'] for instance in cilium_instances['instances'] if 'operator_endpoint' in instance}
    assert all(record['method'] == 'GET' for record in records)
    assert all(record['status'] == 200 for record in records)
    assert all(record['body'] for record in records)

    aggregator.reset()
    replayed = install_replay_session_get(monkeypatch, record_path)
    _run_cilium_check(cilium_instances, dd_run_check)
    _assert_e2e_metrics(aggregator)

    assert replayed == records
