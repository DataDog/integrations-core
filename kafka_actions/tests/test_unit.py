# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401
from unittest.mock import patch

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.kafka_actions import KafkaActionsCheck


def test_check(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = KafkaActionsCheck('kafka_actions', {}, [instance])
    with patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'):
        dd_run_check(check)

    events = [e for e in aggregator.events if e.get('event_type') == 'kafka_action_success']
    assert len(events) == 1, "Expected 1 action success event"
    assert 'produce_message' in events[0]['msg_text']
    assert 'test-read-messages-001' in events[0]['msg_text'] or 'test-config-id' in events[0]['msg_text']
