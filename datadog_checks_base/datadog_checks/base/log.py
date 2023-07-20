# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import sys
import warnings
from typing import Callable  # noqa: F401

from six import PY2, text_type
from urllib3.exceptions import InsecureRequestWarning

from .utils.common import to_native_string
from .utils.tracing import tracing_enabled

try:
    import datadog_agent
except ImportError:
    from .stubs import datadog_agent

# Arbitrary number less than 10 (DEBUG)
TRACE_LEVEL = 7

LOGGER_FRAME_SEARCH_MAX_DEPTH = 50

DEFAULT_FALLBACK_LOGGER = logging.getLogger(__name__)


class AgentLogger(logging.getLoggerClass()):
    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)


class CheckLoggingAdapter(logging.LoggerAdapter):
    def __init__(self, logger, check):
        super(CheckLoggingAdapter, self).__init__(logger, {})
        self.check = check
        self.check_id = self.check.check_id

    def setup_sanitization(self, sanitize):
        # type: (Callable[[str], str]) -> None
        for handler in self.logger.handlers:
            if isinstance(handler, AgentLogHandler):
                handler.setFormatter(SanitizationFormatter(handler.formatter, sanitize=sanitize))

    def process(self, msg, kwargs):
        # Cache for performance
        if not self.check_id:
            self.check_id = self.check.check_id
            # Default to `unknown` for checks that log during
            # `__init__` and therefore have no `check_id` yet
            self.extra['_check_id'] = self.check_id or 'unknown'
            if self.check_id:
                # Break the reference cycle, once we resolved check_id we don't need the check anymore
                self.check = None

        kwargs.setdefault('extra', self.extra)
        return msg, kwargs

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE_LEVEL, msg, *args, **kwargs)

    if PY2:

        def warn(self, msg, *args, **kwargs):
            self.log(logging.WARNING, msg, *args, **kwargs)

        def getEffectiveLevel(self):
            """
            Get the effective level for the underlying logger.
            """
            return self.logger.getEffectiveLevel()


class CheckLogFormatter(logging.Formatter):
    def __init__(self):
        super(CheckLogFormatter, self).__init__()
        self.integration_tracing_enabled, _ = tracing_enabled()

    def format(self, record):
        # type: (logging.LogRecord) -> str
        message = to_native_string(super(CheckLogFormatter, self).format(record))

        if not self.integration_tracing_enabled:
            return "{} | ({}:{}) | {}".format(
                # Default to `-` for non-check logs
                getattr(record, '_check_id', '-'),
                getattr(record, '_filename', record.filename),
                getattr(record, '_lineno', record.lineno),
                message,
            )

        return "{} | ({}:{}) | dd.trace_id={} dd.span_id={} | {}".format(
            getattr(record, '_check_id', '-'),
            getattr(record, '_filename', record.filename),
            getattr(record, '_lineno', record.lineno),
            getattr(record, 'dd.trace_id', 0),
            getattr(record, 'dd.span_id', 0),
            message,
        )


class AgentLogHandler(logging.Handler):
    """
    This handler forwards every log to the Go backend allowing python checks to
    log message within the main agent logging system.
    """

    def __init__(self):
        # type: () -> None
        super(AgentLogHandler, self).__init__()
        self.formatter = CheckLogFormatter()  # type: logging.Formatter

    def emit(self, record):
        # type: (logging.LogRecord) -> None
        message = self.format(record)
        datadog_agent.log(message, record.levelno)


class SanitizationFormatter(logging.Formatter):
    """
    A formatter-like object that sanitizes log messages to hide sensitive data.
    """

    def __init__(self, parent, sanitize):
        # type: (logging.Formatter, Callable[[str], str]) -> None
        self.parent = parent
        self.sanitize = sanitize

    def format(self, record):
        # type: (logging.LogRecord) -> str
        return self.sanitize(self.parent.format(record))


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
    # type: () -> None
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

    # We log instead of emit warnings for unintentionally insecure HTTPS requests
    warnings.simplefilter('ignore', InsecureRequestWarning)

    # `requests` (used in a lot of checks) imports `urllib3`, which logs a bunch of stuff at the info level
    # Therefore, pre emptively increase the default level of that logger to `WARN`
    urllib_logger = logging.getLogger("requests.packages.urllib3")
    urllib_logger.setLevel(logging.WARN)
    urllib_logger.propagate = True


def get_check_logger(default_logger=None):
    """
    Search the current AgentCheck log starting from closest stack frame.

    Caveat: Frame lookup has a cost so the recommended usage is to retrieve and store the logger once
    and avoid calling this method on every check run.
    """
    from datadog_checks.base import AgentCheck

    for i in range(LOGGER_FRAME_SEARCH_MAX_DEPTH):
        try:
            frame = sys._getframe(i)
        except ValueError:
            break
        if 'self' in frame.f_locals:
            check = frame.f_locals['self']
            if isinstance(check, AgentCheck):
                return check.log
    if default_logger is not None:
        return default_logger
    return DEFAULT_FALLBACK_LOGGER
