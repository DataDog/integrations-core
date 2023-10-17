# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import sys
import warnings

import mock
import pytest

from datadog_checks import log
from datadog_checks.base import AgentCheck
from datadog_checks.base.log import DEFAULT_FALLBACK_LOGGER, CheckLogFormatter, get_check_logger, init_logging


def test_get_py_loglevel():
    # default value for invalid input
    assert log._get_py_loglevel(None) == logging.INFO
    # default value for valid unicode input encoding into an invalid key
    assert log._get_py_loglevel(u'dèbùg') == logging.INFO
    # check unicode works
    assert log._get_py_loglevel(u'crit') == logging.CRITICAL
    # check string works
    assert log._get_py_loglevel('crit') == logging.CRITICAL


def test_logging_capture_warnings():
    with mock.patch('logging.Logger.warning') as log_warning:
        warnings.warn("hello-world")  # noqa: B028

        log_warning.assert_not_called()  # warnings are NOT yet captured

        init_logging()  # from here warnings are captured as logs

        warnings.warn("hello-world")  # noqa: B028
        assert log_warning.call_count == 1
        # _showwarning provides only one parameter to Logger.warning on py3.11+ but two before
        # See https://github.com/python/cpython/pull/30975
        # TODO: remove when python 2 is dropped
        warning_arg_index = 0 if sys.version_info >= (3, 11) else 1
        msg = log_warning.mock_calls[0].args[warning_arg_index]
        assert "hello-world" in msg


def test_get_check_logger(caplog):
    class FooConfig(object):
        def __init__(self):
            self.log = get_check_logger()

        def do_something(self):
            self.log.warning("This is a warning")

    class MyCheck(AgentCheck):
        def __init__(self, *args, **kwargs):
            super(MyCheck, self).__init__(*args, **kwargs)
            self._config = FooConfig()

        def check(self, _):
            self._config.do_something()

    check = MyCheck()
    check.check({})

    assert check.log is check._config.log
    assert "This is a warning" in caplog.text


def test_get_check_logger_fallback(caplog):
    log = get_check_logger()

    log.warning("This is a warning")

    assert log is DEFAULT_FALLBACK_LOGGER
    assert "This is a warning" in caplog.text


def test_get_check_logger_argument_fallback(caplog):
    logger = logging.getLogger()
    log = get_check_logger(default_logger=logger)

    log.warning("This is a warning")

    assert log is logger
    assert "This is a warning" in caplog.text


class MockAgentLogHandler(logging.Handler):
    def __init__(self):
        super(MockAgentLogHandler, self).__init__()
        self.formatter = CheckLogFormatter()
        self.records = []

    def emit(self, record):
        self.records.append(self.format(record))


@pytest.mark.parametrize('integration_tracing_enabled', [False, True])
def test_log_trace_context_injection(integration_tracing_enabled):
    def _tracing_enabled():
        return integration_tracing_enabled, False

    with mock.patch('datadog_checks.base.log.tracing_enabled', _tracing_enabled):
        logger = logging.getLogger("test_log_trace_context_injection")
        logger.handlers = []
        handler = MockAgentLogHandler()
        assert handler.formatter.integration_tracing_enabled == integration_tracing_enabled

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.info("hello", extra={'dd.trace_id': 1, 'dd.span_id': 2})

        assert len(handler.records) == 1
        record = handler.records[0]

        if integration_tracing_enabled:
            assert "dd.trace_id=1 dd.span_id=2" in record
        else:
            assert "dd.trace_id=1 dd.span_id=2" not in record
