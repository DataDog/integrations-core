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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_events_test(aggregator, dd_run_check, instance):
    # Mock timestamps instead of using freezegun
    # First run to set the initial timestamp to 2012-01-13
    with mock.patch('datadog_checks.silk.check.get_timestamp', return_value=1326412800) as mock_timestamp:
        check = SilkCheck('silk', {}, [instance])
        assert check.latest_event_query == 1326412800
        mock_timestamp.assert_called_once()

    # Second run to get events between 2012-01-13 and 2012-01-14 and set the timestamp to 2012-01-14
    # Event 1 is between 2012-01-13 and 2012-01-14
    with mock.patch('datadog_checks.silk.check.get_timestamp', return_value=1326499200) as mock_timestamp:
        dd_run_check(check)
        aggregator.assert_event("Event 1", count=1)
        aggregator.assert_event("Event 2", count=0)
        assert check.latest_event_query == 1326499200
        mock_timestamp.assert_called_once()

    # Third run to get events between 2012-01-14 and 2012-01-15
    # Event 2 is between 2012-01-14 and 2012-01-15
    aggregator.reset()
    with mock.patch('datadog_checks.silk.check.get_timestamp', return_value=1326585600) as mock_timestamp:
        dd_run_check(check)
        aggregator.assert_event("Event 1", count=0)
        aggregator.assert_event("Event 2", count=1)
        assert check.latest_event_query == 1326585600
        mock_timestamp.assert_called_once()
