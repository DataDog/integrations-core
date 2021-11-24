# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.testing import requires_py3, requires_windows
from datadog_checks_base.datadog_checks.base.checks.windows.perf_counters.connection import Connection

from .utils import SERVER, get_check

try:
    from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheck
    from datadog_checks.base.checks.windows.perf_counters.counter import PerfObject
# non-Windows systems
except Exception:
    PerfCountersBaseCheck = object
    PerfObject = object

pytestmark = [requires_py3, requires_windows, pytest.mark.perf_counters]

def test_connection_server_name():
    check = get_check()
    connection = Connection(check.instance)
    assert connection.server == SERVER

def test_connection_server_name_fqdn():
    check = get_check(instance=[{'server': 'qa-windows.c.datadog-agent-qa-lab.internal'}])
    connection = Connection(check.instance)
    assert connection.server == SERVER