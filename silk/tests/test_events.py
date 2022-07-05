# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os

import mock
import pytest

from datadog_checks.dev.fs import read_file
from datadog_checks.silk import SilkCheck
from datadog_checks.silk.events import SilkEvent

from .conftest import HERE


def mock_get_raw_events(file):
    file_contents = read_file(os.path.join(HERE, 'fixtures', file))
    response = json.loads(file_contents)

    return [(response, 200)]


def test_event_payload():
    sample_raw_event = {
        "event_id": 11,
        "id": 2,
        "labels": "EVENT, ACTION",
        "level": "INFO",
        "message": "Event logging started",
        "name": "EVENT_LOGGING_STARTED",
        "timestamp": 1638831003.782305,
        "user": "Internal",
    }

    expected_event_payload = {
        "msg_title": "EVENT_LOGGING_STARTED",
        "msg_text": "Event logging started",
        "timestamp": 1638831003.782305,
        "tags": ["test:silk", "user:Internal"],
        "event_type": "EVENT, ACTION",
        "alert_type": "info",
    }

    normalized_event = SilkEvent(sample_raw_event, ["test:silk"])
    actual_payload = normalized_event.get_datadog_payload()
    assert actual_payload == expected_event_payload


def test_latest_event_query(aggregator, instance, dd_run_check):
    check = SilkCheck('silk', {}, [instance])
    check.latest_event_query = 123
    check._get_data = mock.MagicMock(side_effect=mock_get_raw_events("events.json"))
    check.collect_events([])

    aggregator.assert_event("test_event1", count=1)
    aggregator.assert_event("test_event2", count=1)


@pytest.mark.parametrize(
    'file, log_warning',
    [
        ("events_no_timestamp.json", "Event has no timestamp, will not submit event"),
        ("events_no_title.json", "Event has no name, will not submit event"),
        ("events_no_message.json", "Event has no message, will not submit event"),
    ],
)
def test_malformed_event(aggregator, instance, dd_run_check, file, log_warning, caplog):
    caplog.clear()
    caplog.set_level(logging.WARNING)
    check = SilkCheck('silk', {}, [instance])
    check._get_data = mock.MagicMock(side_effect=mock_get_raw_events(file))
    check.collect_events([])

    aggregator.assert_event("test_event1", count=0)
    assert log_warning in caplog.text
