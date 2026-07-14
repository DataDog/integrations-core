# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time

import mock
import pytest
from confluent_kafka.error import KafkaError

from datadog_checks.kafka_consumer.leader_election import LeaderElection

pytestmark = [pytest.mark.unit]


def make_election(interval=60):
    check = mock.MagicMock()
    client = mock.MagicMock()
    config = mock.MagicMock()
    config._auto_load_distribution_interval = interval
    config._request_timeout = 5
    config._custom_tags = ['env:test']
    log = mock.MagicMock()

    election = LeaderElection(check, client, config, log)
    election._consumer = client.build_election_consumer.return_value
    election._producer = client.build_election_producer.return_value
    return election, check, client


def make_message(value=None, error=None):
    message = mock.MagicMock()
    message.error.return_value = error
    message.value.return_value = value
    return message


def make_eof_error():
    error = mock.MagicMock()
    error.code.return_value = KafkaError._PARTITION_EOF
    return error


def timestamp_payload(age_seconds):
    return json.dumps({"timestamp": time.time() - age_seconds}).encode()


def test_no_assignment_yet_stands_down():
    election, check, _ = make_election()
    election._consumer.poll.return_value = None

    assert election.should_collect() is False
    check.gauge.assert_called_once_with('leader_election.is_leader', 0, tags=['env:test'])


def test_partition_eof_bootstraps_collection():
    election, check, _ = make_election()
    election._consumer.poll.return_value = make_message(error=make_eof_error())

    assert election.should_collect() is True
    check.gauge.assert_called_once_with('leader_election.is_leader', 1, tags=['env:test'])
    assert election._pending_commit_message is None


def test_fresh_message_skips_without_committing():
    election, check, _ = make_election(interval=60)
    election._consumer.poll.return_value = make_message(value=timestamp_payload(age_seconds=5))

    assert election.should_collect() is False
    check.gauge.assert_called_once_with('leader_election.is_leader', 0, tags=['env:test'])

    election.finish()
    election._consumer.commit.assert_not_called()


def test_stale_message_collects_and_commit_happens_on_finish():
    election, check, _ = make_election(interval=60)
    message = make_message(value=timestamp_payload(age_seconds=120))
    election._consumer.poll.return_value = message

    assert election.should_collect() is True
    check.gauge.assert_called_once_with('leader_election.is_leader', 1, tags=['env:test'])
    assert election._pending_commit_message is message

    election.finish()

    election._producer.produce.assert_called_once()
    election._producer.flush.assert_called_once()
    election._consumer.commit.assert_called_once_with(message=message, asynchronous=False)
    assert election._collecting_this_round is False


def test_finish_is_a_noop_when_standing_down():
    election, _, _ = make_election()
    election._consumer.poll.return_value = None

    election.should_collect()
    election.finish()

    election._producer.produce.assert_not_called()
    election._consumer.commit.assert_not_called()


def test_heartbeat_keeps_polling_during_collection():
    election, _, _ = make_election()
    election._consumer.poll.return_value = make_message(error=make_eof_error())
    election.should_collect()

    with mock.patch('datadog_checks.kafka_consumer.leader_election.HEARTBEAT_TICK_SECONDS', 0.01):
        election.start_heartbeat()
        time.sleep(0.05)
        election.finish()

    # At least one heartbeat tick (poll(0)) plus the initial should_collect() poll.
    poll_calls = [call for call in election._consumer.poll.call_args_list if call.args == (0,)]
    assert len(poll_calls) >= 1
