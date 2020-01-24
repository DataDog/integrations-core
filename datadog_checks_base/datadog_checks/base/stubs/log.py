# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from ..log import CheckLoggingAdapter as AgentLoggingAdapter

TRACE_LEVEL = 7


Logger = logging.Logger

# Weird flex, but static type checkers need a statically-defined base class, so
# we must assign the dynamic logger class in a type-ignored branch.
if True:
    Logger = logging.getLoggerClass()  # type: ignore


class AgentLogger(Logger):
    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        raise NotImplementedError('The critical log level is reserved for agent shutdowns.')


class CheckLoggingAdapter(AgentLoggingAdapter):
    def critical(self, msg, *args, **kwargs):
        raise NotImplementedError('The critical log level is reserved for agent shutdowns.')


def init_logging():
    logging.addLevelName(TRACE_LEVEL, 'TRACE')
    logging.setLoggerClass(AgentLogger)
