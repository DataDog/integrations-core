# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from mock import MagicMock, patch

from datadog_checks.nagios import NagiosCheck
from datadog_checks.nagios.nagios import NagiosEventLogTailer

from .common import CHECK_NAME, CUSTOM_TAGS, NAGIOS_TEST_LOG

# Random test values
METRIC_NAME = 'nagios.metric_name'
METRIC_VALUE = 42
METRIC_TAGS = CUSTOM_TAGS
METRIC_TIMESTAMP = 1337404007


class TestGaugeWrapper:
    def test_gauge_without_timestamp(self):
        """
        Test the 'gauge' wrapper to see if it strips the 'timestamp' arg for gauge functions that do not accept it
        """

        def gauge_v6(self, name, value, tags=None, hostname=None, device_name=None):
            """
            A gauge function that does not accept the 'timestamp' argument
            """
            # Make sure we get the original arguments back and timestamp is not being received
            assert name == METRIC_NAME
            assert value == METRIC_VALUE
            assert tags == METRIC_TAGS
            assert hostname is None
            assert device_name is None

        # This should call 'gauge_v6' with all the same arguments that we passed in, except for the 'timestamp' argument
        with patch('datadog_checks.checks.AgentCheck.gauge', new=gauge_v6):
            nagios = NagiosCheck(CHECK_NAME, {}, {})
            nagios.gauge(METRIC_NAME, METRIC_VALUE, tags=METRIC_TAGS, timestamp=METRIC_TIMESTAMP)

    def test_gauge_with_timestamp(self):
        """
        Test the 'gauge' wrapper to see if it doesn't strip anything for gauge functions that accept timestamps
        """

        def gauge_v5(self, metric, value, tags=None, hostname=None, device_name=None, timestamp=None):
            """
            A gauge function that should accept the 'timestamp' argument
            """
            # Make sure we get the original arguments back
            assert metric == METRIC_NAME
            assert value == METRIC_VALUE
            assert tags == METRIC_TAGS
            assert hostname is None
            assert device_name is None
            assert timestamp == METRIC_TIMESTAMP

        # This should call 'gauge_v5' with all the same arguments that we passed in
        with patch('datadog_checks.checks.AgentCheck.gauge', new=gauge_v5):
            nagios = NagiosCheck(CHECK_NAME, {}, {})
            nagios.gauge(METRIC_NAME, METRIC_VALUE, tags=METRIC_TAGS, timestamp=METRIC_TIMESTAMP)


def test_centreon_event_logs():
    log = (
        "[1571848012] [53365] SERVICE ALERT: SOMEHOST;Current Anonymous Users;CRITICAL;SOFT;1;"
        "CHECK_NRPE: Socket timeout after 60 seconds."
    )
    events = []
    mock_log = MagicMock()
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, None, mock_log, "host", [], events.append, None, 5)
    tailer._parse_line(log)
    assert len(events) == 1
    assert events[0]['event_type'] == 'SERVICE ALERT'
    assert events[0]['host'] == 'SOMEHOST'
