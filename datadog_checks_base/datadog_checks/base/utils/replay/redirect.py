# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import sys

from datadog_checks.base.checks import base
from datadog_checks.base.log import LOG_LEVEL_MAP, TRACE_LEVEL, _get_py_loglevel
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.format import json
from datadog_checks.base.utils.metadata import core
from datadog_checks.base.utils.replay.constants import KNOWN_DATADOG_AGENT_SETTER_METHODS, EnvVars

MESSAGE_INDICATOR = os.environ[EnvVars.MESSAGE_INDICATOR]
LOG_METHODS = {log_level: log_method.lower() for log_method, log_level in LOG_LEVEL_MAP.items()}


class ReplayAggregator(object):
    GAUGE, RATE, COUNT, MONOTONIC_COUNT, COUNTER, HISTOGRAM, HISTORATE = range(7)

    def __getattr__(self, name):
        method = self.method_generator(name)
        setattr(self, name, method)
        return method

    @staticmethod
    def method_generator(method_name):
        def method(*args, **kwargs):
            print(
                '{}:aggregator:{}'.format(
                    MESSAGE_INDICATOR,
                    to_native_string(json.encode({'method': method_name, 'args': list(args)[1:], 'kwargs': kwargs})),
                )
            )

        return method


class ReplayDatadogAgent(object):
    def __getattr__(self, name):
        method = self.method_generator(name, name not in KNOWN_DATADOG_AGENT_SETTER_METHODS)
        setattr(self, name, method)
        return method

    @staticmethod
    def method_generator(method_name, read):
        def method(*args, **kwargs):
            print(
                '{}:datadog_agent:{}'.format(
                    MESSAGE_INDICATOR,
                    to_native_string(json.encode({'method': method_name, 'args': list(args), 'kwargs': kwargs})),
                )
            )
            if read:
                return json.decode(sys.stdin.readline())['value']

        return method


class ReplayLogger(logging.Logger):
    def log(self, level, *args, **kwargs):
        print(
            '{}:log:{}'.format(
                MESSAGE_INDICATOR,
                to_native_string(json.encode({'method': LOG_METHODS[level], 'args': [str(a) for a in args]})),
            )
        )


base.AGENT_RUNNING = True
base.aggregator = ReplayAggregator()
base.datadog_agent = core.datadog_agent = ReplayDatadogAgent()

logging.addLevelName(TRACE_LEVEL, 'TRACE')
logging.setLoggerClass(ReplayLogger)
logging.getLogger().setLevel(_get_py_loglevel(base.datadog_agent.get_config('log_level')))


def run_check(check_class):
    check = check_class(
        os.environ[EnvVars.CHECK_NAME],
        json.decode(os.environ[EnvVars.INIT_CONFIG]),
        [json.decode(os.environ[EnvVars.INSTANCE])],
    )
    check.check_id = os.environ[EnvVars.CHECK_ID]

    result = check.run()
    if result:
        print('{}:error:{}'.format(MESSAGE_INDICATOR, result))
