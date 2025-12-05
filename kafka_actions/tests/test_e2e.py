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

    # Find the action success event
    action_events = [e for e in events if 'kafka_action_' in e.get('event_type', '')]
    assert len(action_events) == 1, f"Expected 1 action event, got {len(action_events)}"

    action_event = action_events[0]
    assert action_event['event_type'] == 'kafka_action_success'
    assert 'kafka_cluster_id' in [tag.split(':')[0] for tag in action_event['tags']]
    assert 'remote_config_id:test-rc-id' in action_event['tags']

    # Parse the msg_text as JSON
    event_data = json.loads(action_event['msg_text'])
    assert event_data['action'] == 'read_messages'
    assert event_data['status'] == 'success'
    assert 'stats' in event_data
    stats = event_data['stats']
    assert stats['messages_scanned'] > 0
    assert stats['messages_sent'] > 0

    # Check that message events were emitted
    message_events = [e for e in events if e.get('event_type') == 'kafka_message']
    assert len(message_events) > 0, "Expected at least one Kafka message event"
    assert len(message_events) == stats['messages_sent'], "Message event count should match stats"

    # Verify message event structure
    msg_event = message_events[0]
    assert msg_event['source_type_name'] == 'kafka'
    assert 'kafka_cluster_id' in [tag.split(':')[0] for tag in msg_event['tags']]
    assert 'remote_config_id:test-rc-id' in msg_event['tags']

    # Parse message event data
    msg_data = json.loads(msg_event['msg_text'])
    assert 'topic' in msg_data
    assert 'partition' in msg_data
    assert 'offset' in msg_data
    assert 'key' in msg_data
    assert 'value' in msg_data
    assert msg_data['topic'] == 'test-topic'

    # Find the action success event
    action_events = [e for e in events if 'kafka_action_' in e.get('event_type', '')]
    assert len(action_events) == 1, f"Expected 1 action event, got {len(action_events)}"

    action_event = action_events[0]
    assert action_event['event_type'] == 'kafka_action_success'
    assert 'kafka_cluster_id' in [tag.split(':')[0] for tag in action_event['tags']]
    assert 'remote_config_id:test-rc-id' in action_event['tags']

    # Parse the msg_text as JSON
    event_data = json.loads(action_event['msg_text'])
    assert event_data['action'] == 'read_messages'
    assert event_data['status'] == 'success'
    assert 'stats' in event_data
    stats = event_data['stats']
    assert stats['messages_scanned'] > 0
    assert stats['messages_sent'] > 0

    # Check that message events were emitted
    message_events = [e for e in events if e.get('event_type') == 'kafka_message']
    assert len(message_events) > 0, "Expected at least one Kafka message event"
    assert len(message_events) == stats['messages_sent'], "Message event count should match stats"

    # Verify message event structure
    msg_event = message_events[0]
    assert msg_event['source_type_name'] == 'kafka'
    assert 'kafka_cluster_id' in [tag.split(':')[0] for tag in msg_event['tags']]
    assert 'remote_config_id:test-rc-id' in msg_event['tags']

    # Parse message event data
    msg_data = json.loads(msg_event['msg_text'])
    assert 'topic' in msg_data
    assert 'partition' in msg_data
    assert 'offset' in msg_data
    assert 'key' in msg_data
    assert 'value' in msg_data
    assert msg_data['topic'] == 'test-topic'
