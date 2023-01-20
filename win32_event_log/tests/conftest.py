# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
import time
from copy import deepcopy

import pytest
import win32evtlog

from datadog_checks.win32_event_log import Win32EventLogCheck

from . import common


class EventReporter(object):
    EVENT_TYPES = {
        'info': win32evtlog.EVENTLOG_INFORMATION_TYPE,
        'warning': win32evtlog.EVENTLOG_WARNING_TYPE,
        'error': win32evtlog.EVENTLOG_ERROR_TYPE,
    }

    def __init__(self, source):
        self.source = source
        self.log_handle = None

    def report(self, *args, **kwargs):
        thread = threading.Thread(target=self._report, args=args, kwargs=kwargs)
        thread.start()
        return thread

    def _report(self, message, wait=1, level='info', event_type=None):
        # Sleep to allow check run to commence
        time.sleep(wait)

        # https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-reporteventa
        # https://mhammond.github.io/pywin32/win32evtlog__ReportEvent_meth.html
        win32evtlog.ReportEvent(
            self.log_handle,
            event_type if event_type is not None else self.EVENT_TYPES[level],
            common.EVENT_CATEGORY,
            common.EVENT_ID,
            None,
            message.splitlines(),
            None,
        )

    def __enter__(self):
        # This requires that tests are executed in an administrator shell, useful for testing handling of Error 15027
        # win32evtlogutil.AddSourceToRegistry(self.source)

        # https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-registereventsourcea
        # https://mhammond.github.io/pywin32/win32evtlog__RegisterEventSource_meth.html
        self.log_handle = win32evtlog.RegisterEventSource(None, self.source)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-deregistereventsource
        # https://mhammond.github.io/pywin32/win32evtlog__DeregisterEventSource_meth.html
        win32evtlog.DeregisterEventSource(self.log_handle)

        # This requires that tests are executed in an administrator shell, useful for testing handling of Error 15027
        # win32evtlogutil.RemoveSourceFromRegistry(self.source)


@pytest.fixture(scope='session')
def event_reporter():
    with EventReporter(common.EVENT_SOURCE) as er:
        yield er


@pytest.fixture
def report_event(event_reporter):
    threads = []

    def _report_event(*args, **kwargs):
        threads.append(event_reporter.report(*args, **kwargs))

    try:
        yield _report_event
    finally:
        for thread in threads:
            thread.join()


@pytest.fixture(scope='session')
def new_check():
    return lambda instance, init_config=None: Win32EventLogCheck('win32_event_log', init_config or {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.fixture(scope='session')
def dd_environment():  # no cov
    yield common.INSTANCE, {'docker_platform': 'windows'}
