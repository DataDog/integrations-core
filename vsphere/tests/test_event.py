# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.vsphere import VSphereCheck

from .legacy.utils import mock_alarm_event


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_events_time(aggregator, dd_run_check, realtime_instance, datadog_agent):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.initiate_api_connection()

    event1 = mock_alarm_event(from_status='green', key=10)
    event2 = mock_alarm_event(from_status='yellow', key=20)
    event3 = mock_alarm_event(from_status='red', key=30)

    check.check(None)
    assert len(aggregator.events) == 0
    assert check.latest_processed_events == []

    check.api.mock_events = [event1]
    check.check(None)
    aggregator.assert_event("vCenter monitor status changed on this alarm, it was green and it's now red.", count=1)
    assert len(aggregator.events) == 1
    assert check.latest_processed_events == [10]

    aggregator.reset()

    check.api.mock_events = [event1, event2, event3]
    check.check(None)
    for status, count in [('yellow', 1), ('red', 1), ('green', 0)]:
        aggregator.assert_event(
            "vCenter monitor status changed on this alarm, it was {} and it's now red.".format(status), count=count
        )
    assert len(aggregator.events) == 2
    assert check.latest_processed_events == [20, 30]
