# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from datadog_checks.dev._env import e2e_testing

from . import common

pytestmark = [pytest.mark.e2e]


def test_e2e_read_messages(dd_environment, kafka_instance, check, dd_run_check, aggregator):
    """Test reading messages from Kafka."""
    if not e2e_testing():
        pytest.skip("E2E tests require dd_environment fixture")

    # Verify cluster is available
    cluster_id = common.get_cluster_id()
    assert cluster_id is not None, "Kafka cluster is not available"

    # Ensure the instance has the cluster ID set
    kafka_instance['read_messages']['cluster'] = cluster_id

    # Run the check
    check_instance = check(kafka_instance)
    dd_run_check(check_instance)

    # Verify events were emitted
    events = aggregator.events
    assert len(events) > 0, f"Expected at least one event. Got {len(events)} events."

    # Find the action success event in standard Datadog events
    action_events = [e for e in events if 'kafka_action_' in e.get('event_type', '')]
    assert len(action_events) == 1, f"Expected 1 action event, got {len(action_events)}"

    action_event = action_events[0]
    assert action_event['event_type'] == 'kafka_action_success'
    assert 'kafka_cluster_id' in [tag.split(':')[0] for tag in action_event['tags']]
    assert 'remote_config_id:test-rc-id' in action_event['tags']
    assert action_event['remote_config_id'] == 'test-rc-id'
    assert 'kafka_cluster_id' in action_event

    # Parse the msg_text as JSON
    event_data = json.loads(action_event['msg_text'])
    assert event_data['action'] == 'read_messages'
    assert event_data['status'] == 'success'
    assert event_data['remote_config_id'] == 'test-rc-id'
    assert 'kafka_cluster_id' in event_data
    assert 'message_timestamp' in event_data
    assert 'stats' in event_data
    stats = event_data['stats']
    assert stats['messages_scanned'] > 0
    assert stats['messages_sent'] > 0

    # Check that action event was also sent to Data Streams track
    data_streams_events = aggregator.get_event_platform_events("data-streams-message")
    action_ds_events = [e for e in data_streams_events if 'action' in e]
    assert len(action_ds_events) == 1, f"Expected 1 action event in data streams, got {len(action_ds_events)}"

    action_ds_event = action_ds_events[0]
    assert action_ds_event['action'] == 'read_messages'
    assert action_ds_event['status'] == 'success'
    assert action_ds_event['remote_config_id'] == 'test-rc-id'
    assert 'kafka_cluster_id' in action_ds_event
    assert 'message_timestamp' in action_ds_event
    assert 'stats' in action_ds_event
    assert action_ds_event['stats']['messages_scanned'] > 0
    assert action_ds_event['stats']['messages_sent'] > 0

    # Verify action event payload is the same in both tracks
    assert action_ds_event == event_data, "Action event should have same payload in both tracks"

    # Check that Kafka message events were emitted to data-streams-message track ONLY
    message_events = [e for e in data_streams_events if 'topic' in e]
    assert len(message_events) > 0, "Expected at least one Kafka message event in data-streams track"
    assert len(message_events) == stats['messages_sent'], "Message event count should match stats"

    # Verify message event structure
    msg_event = message_events[0]
    assert msg_event['remote_config_id'] == 'test-rc-id'
    assert 'kafka_cluster_id' in msg_event
    assert msg_event['topic'] == 'test-topic'
    assert 'partition' in msg_event
    assert 'offset' in msg_event
    assert 'key' in msg_event
    assert 'value' in msg_event
    assert 'message_timestamp' in msg_event

    # Verify message has actual content
    assert msg_event['partition'] >= 0
    assert msg_event['offset'] >= 0
