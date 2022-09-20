# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import sys

from datadog_checks.base import to_native_string
from datadog_checks.base.checks import base
from datadog_checks.base.log import LOG_LEVEL_MAP
from datadog_checks.base.utils.metadata import core
from datadog_checks.base.utils.serialization import json
from datadog_checks.ibm_mq import IbmMqCheck
from datadog_checks.ibm_mq.constants import KNOWN_DATADOG_AGENT_SETTER_METHODS

MESSAGE_INDICATOR = os.environ['REPLAY_MESSAGE_INDICATOR']
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
                    to_native_string(json.dumps({'method': method_name, 'args': list(args)[1:], 'kwargs': kwargs})),
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
                    to_native_string(json.dumps({'method': method_name, 'args': list(args), 'kwargs': kwargs})),
                )
            )
            if read:
                return json.loads(sys.stdin.readline())['value']

        return method


class ReplayLogger(logging.Logger):
    def log(self, level, *args, **kwargs):
        print(
            '{}:log:{}'.format(
                MESSAGE_INDICATOR,
                to_native_string(json.dumps({'method': LOG_METHODS[level], 'args': [str(a) for a in args]})),
            )
        )


base.using_stub_aggregator = False
base.aggregator = ReplayAggregator()
base.datadog_agent = core.datadog_agent = ReplayDatadogAgent()
logging.setLoggerClass(ReplayLogger)


def main():
    check = IbmMqCheck(
        'ibm_mq', json.loads(os.environ['REPLAY_INIT_CONFIG']), [json.loads(os.environ['REPLAY_INSTANCE'])]
    )
    check.check_id = os.environ['REPLAY_CHECK_ID']

    result = check.run()
    if result:
        print('{}:error:{}'.format(MESSAGE_INDICATOR, result))
