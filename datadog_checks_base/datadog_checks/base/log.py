# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Callable

from six import PY2, iteritems, text_type

from .utils.common import to_native_string

try:
    import datadog_agent
except ImportError:
    from .stubs import datadog_agent


# Arbitrary number less than 10 (DEBUG)
TRACE_LEVEL = 7


class AgentLogger(logging.getLoggerClass()):
    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)


class CheckLoggingAdapter(logging.LoggerAdapter):
    def __init__(self, logger, check):
        super(CheckLoggingAdapter, self).__init__(logger, {})
        self.check = check
        self.check_id = self.check.check_id

    def process(self, msg, kwargs):
        # Cache for performance
        if not self.check_id:
            self.check_id = self.check.check_id
            # Default to `unknown` for checks that log during
            # `__init__` and therefore have no `check_id` yet
            self.extra['_check_id'] = self.check_id or 'unknown'

        kwargs.setdefault('extra', self.extra)
        return msg, kwargs

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE_LEVEL, msg, *args, **kwargs)

    if PY2:

        def warn(self, msg, *args, **kwargs):
            self.log(logging.WARNING, msg, *args, **kwargs)


class AgentLogHandler(logging.Handler):
    """
    This handler forwards every log to the Go backend allowing python checks to
    log message within the main agent logging system.
    """

    def emit(self, record):
        msg = "{} | ({}:{}) | {}".format(
            # Default to `-` for non-check logs
            getattr(record, '_check_id', '-'),
            getattr(record, '_filename', record.filename),
            getattr(record, '_lineno', record.lineno),
            to_native_string(self.format(record)),
        )
        datadog_agent.log(msg, record.levelno)


class SanitizationFilter(logging.Filter):
    """
    A filter for sanitizing log records messages.
    """

    def __init__(self, name, sanitize):
        # type: (str, Callable[[str], str]) -> None
        super(SanitizationFilter, self).__init__(name)
        self.sanitize = sanitize

    def filter(self, record):
        # type: (logging.LogRecord) -> bool
        record.msg = self.sanitize(to_native_string(record.msg))

        if isinstance(record.args, dict):
            record.args = {key: self.sanitize(value) for key, value in iteritems(record.args)}
        else:
            record.args = tuple(self.sanitize(arg) for arg in record.args)

        return True


LOG_LEVEL_MAP = {
    'CRIT': logging.CRITICAL,
    'CRITICAL': logging.CRITICAL,
    'ERR': logging.ERROR,
    'ERROR': logging.ERROR,
    'WARN': logging.WARNING,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'TRACE': TRACE_LEVEL,
}


def _get_py_loglevel(lvl):
    """
    Map log levels to strings
    """
    # In Python2, transform the unicode object into plain string
    if PY2 and isinstance(lvl, text_type):
        lvl = lvl.encode('ascii', 'ignore')

    # Be resilient to bad input since `lvl` comes from a configuration file
    try:
        lvl = lvl.upper()
    except AttributeError:
        lvl = ''

    # if `lvl` is not a valid level string, let it fall back to default logging value
    return LOG_LEVEL_MAP.get(lvl, logging.INFO)


def init_logging():
    """
    Initialize logging (set up forwarding to Go backend and sane defaults)
    """
    # Forward to Go backend
    logging.addLevelName(TRACE_LEVEL, 'TRACE')
    logging.setLoggerClass(AgentLogger)
    logging.captureWarnings(True)  # Capture warnings as logs so it's easier for log parsers to handle them.

    rootLogger = logging.getLogger()
    rootLogger.addHandler(AgentLogHandler())
    rootLogger.setLevel(_get_py_loglevel(datadog_agent.get_config('log_level')))

    # `requests` (used in a lot of checks) imports `urllib3`, which logs a bunch of stuff at the info level
    # Therefore, pre emptively increase the default level of that logger to `WARN`
    urllib_logger = logging.getLogger("requests.packages.urllib3")
    urllib_logger.setLevel(logging.WARN)
    urllib_logger.propagate = True
