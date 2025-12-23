# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from datadog_checks.dev._env import e2e_testing

from . import common

pytestmark = [pytest.mark.e2e]


def test_e2e_read_messages(dd_environment, kafka_instance, check, dd_run_check, aggregator):
    """Test end-to-end integration: check can connect to real Kafka and emit events correctly."""
    if not e2e_testing():
        pytest.skip("E2E tests require dd_environment fixture")

    # Verify cluster is available
    cluster_id = common.get_cluster_id()
    assert cluster_id is not None, "Kafka cluster is not available"

    kafka_instance['read_messages']['cluster'] = cluster_id

    # Run the check
    check_instance = check(kafka_instance)
    dd_run_check(check_instance)

    # Verify standard Datadog event was emitted
    action_events = [e for e in aggregator.events if 'kafka_action_' in e.get('event_type', '')]
    assert len(action_events) == 1, f"Expected 1 action event, got {len(action_events)}"
    assert action_events[0]['event_type'] == 'kafka_action_success'

    # Verify events sent to data-streams-message track
    data_streams_events = aggregator.get_event_platform_events("data-streams-message")
    action_ds_events = [e for e in data_streams_events if 'action' in e]
    message_events = [e for e in data_streams_events if 'topic' in e]

    # Verify both action and message events were sent
    assert len(action_ds_events) == 1, f"Expected 1 action event in data streams, got {len(action_ds_events)}"
    assert len(message_events) > 0, "Expected at least one Kafka message event"

    # Verify action event payload is consistent between both tracks
    event_data = json.loads(action_events[0]['msg_text'])
    assert action_ds_events[0] == event_data, "Action event should have same payload in both tracks"

    # Verify message count matches stats
    stats = event_data['stats']
    assert len(message_events) == stats['messages_sent'], "Message event count should match stats"
