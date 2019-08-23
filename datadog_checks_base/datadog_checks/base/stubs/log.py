# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

TRACE_LEVEL = 7


class AgentLogger(logging.getLoggerClass()):
    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        raise NotImplementedError('The critical log level is reserved for agent shutdowns.')


class CheckLoggingAdapter(logging.LoggerAdapter):
    def __init__(self, logger, check):
        super(CheckLoggingAdapter, self).__init__(logger, {})
        self.check = check
        self.check_id = self.check.check_id

    def process(self, msg, kwargs):
        if not self.check_id:
            self.check_id = self.check.check_id
            self.extra['_check_id'] = self.check_id or 'unknown'

        kwargs['extra'] = self.extra
        return msg, kwargs

    def trace(self, msg, *args, **kwargs):
        self.log(TRACE_LEVEL, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        raise NotImplementedError('The critical log level is reserved for agent shutdowns.')


def init_logging():
    logging.addLevelName(TRACE_LEVEL, 'TRACE')
    logging.setLoggerClass(AgentLogger)
