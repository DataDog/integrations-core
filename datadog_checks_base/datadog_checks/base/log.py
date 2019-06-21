# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from six import PY2, text_type

from .utils.common import to_string

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


class AgentLogHandler(logging.Handler):
    """
    This handler forwards every log to the Go backend allowing python checks to
    log message within the main agent logging system.
    """

    def emit(self, record):
        msg = "({}:{}) | {}".format(
            getattr(record, '_filename', record.filename),
            getattr(record, '_lineno', record.lineno),
            to_string(self.format(record)),
        )
        datadog_agent.log(msg, record.levelno)


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
    rootLogger = logging.getLogger()
    rootLogger.addHandler(AgentLogHandler())
    rootLogger.setLevel(_get_py_loglevel(datadog_agent.get_config('log_level')))

    # `requests` (used in a lot of checks) imports `urllib3`, which logs a bunch of stuff at the info level
    # Therefore, pre emptively increase the default level of that logger to `WARN`
    urllib_logger = logging.getLogger("requests.packages.urllib3")
    urllib_logger.setLevel(logging.WARN)
    urllib_logger.propagate = True
