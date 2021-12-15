# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import mock
import pytest

from datadog_checks.dev.fs import read_file
from datadog_checks.silk import SilkCheck
from datadog_checks.silk.events import SilkEvent

from .conftest import HERE

SAMPLE_RAW_EVENT = {
    "event_id": 11,
    "id": 2,
    "labels": "EVENT, ACTION",
    "level": "INFO",
    "message": "Event logging started",
    "name": "EVENT_LOGGING_STARTED",
    "timestamp": 1638831003.782305,
    "user": "Internal",
}

EXPECTED_EVENT_PAYLOAD = {
    "msg_title": "EVENT_LOGGING_STARTED",
    "msg_text": "Event logging started",
    "timestamp": 1638831003.782305,
    "tags": ["test:silk", "user:Internal"],
    "event_type": "EVENT, ACTION",
    "alert_type": "info",
    "source_type_name": "silk",
}


def mock_get_raw_events(*args):
    response = mock.MagicMock()

    file_contents = read_file(os.path.join(HERE, 'fixtures', 'events?timestamp__gte=123.json'))
    response = json.loads(file_contents)

    return response, 200


def test_event_payload():
    normalized_event = SilkEvent(SAMPLE_RAW_EVENT, ["test:silk"])
    actual_payload = normalized_event.get_datadog_payload()
    assert actual_payload == EXPECTED_EVENT_PAYLOAD


@pytest.mark.usefixtures('dd_environment')
def test_latest_event_query(aggregator, instance, dd_run_check):
    check = SilkCheck('silk', {}, [instance])
    check.latest_event_query = 123
    check.get_metrics = mock.MagicMock(side_effect=mock_get_raw_events)
    check.collect_events()

    aggregator.assert_event("test_event1", count=1)
    aggregator.assert_event("test_event2", count=1)
