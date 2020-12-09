# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from mock import MagicMock

from datadog_checks.nagios.nagios import NagiosEventLogTailer

from .common import NAGIOS_TEST_LOG


def test_centreon_event_logs():
    log = (
        "[1571848012] [53365] SERVICE ALERT: SOMEHOST;Current Anonymous Users;CRITICAL;SOFT;1;"
        "CHECK_NRPE: Socket timeout after 60 seconds."
    )
    events = []
    mock_log = MagicMock()
    tailer = NagiosEventLogTailer(NAGIOS_TEST_LOG, mock_log, "host", events.append, None, False)
    tailer.parse_line(log)
    assert len(events) == 1
    assert events[0]['event_type'] == 'SERVICE ALERT'
    assert events[0]['host'] == 'SOMEHOST'
