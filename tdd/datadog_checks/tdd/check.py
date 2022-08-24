# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datadog_checks.base import AgentCheck
from datadog_checks.tdd.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES, METRICS


class TddCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'tdd'

    def __init__(self, name, init_config, instances):
        super(TddCheck, self).__init__(name, init_config, instances)
        options = {
            'host': self.instance.get('hosts', 'localhost:27017'),
            'serverSelectionTimeoutMS': self.instance.get('timeout', 5) * 1000,
        }
        self._mongo_client = MongoClient(**options)
        self._mongo_version = None

    def check(self, _):
        try:
            # The ping command is cheap and does not require auth.
            ping_output = self._mongo_client['admin'].command('ping')
            self.log.debug('ping_output: %s', ping_output)
            if ping_output['ok'] == 1:
                self.log.debug('Connected')
                self.service_check("can_connect", AgentCheck.OK)
                self._mongo_version = self._mongo_client.server_info().get('version', '0.0.0')
                self.set_metadata('version', self._mongo_version)
                self.log.debug('mongo_version: %s', self._mongo_version)
                server_status_output = self._mongo_client['admin'].command('serverStatus')
                self.log.debug('server_status_output: %s', server_status_output)
                for metric_name in METRICS:
                    value = server_status_output
                    try:
                        for c in metric_name.split("."):
                            value = value[c]
                    except KeyError:
                        continue
                    submit_method = (
                        METRICS[metric_name][0] if isinstance(METRICS[metric_name], tuple) else METRICS[metric_name]
                    )
                    metric_name_alias = (
                        METRICS[metric_name][1] if isinstance(METRICS[metric_name], tuple) else metric_name
                    )
                    metric_name_alias = self._normalize(metric_name_alias, submit_method, "")
                    self.log.debug(
                        '%s: %s [alias: %s, method: %s]', metric_name, value, metric_name_alias, submit_method
                    )
                    submit_method(self, metric_name_alias, value)
            else:
                self.log.error('ping returned no valid value')
                self.service_check("can_connect", AgentCheck.CRITICAL)
        except (ConnectionFailure, Exception) as e:
            self.log.error('Exception: %s', e)
            self.service_check("can_connect", AgentCheck.CRITICAL)

    def _normalize(self, metric_name, submit_method, prefix=None):
        """Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "" if not prefix else prefix
        metric_suffix = "ps" if submit_method == AgentCheck.rate else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in CASE_SENSITIVE_METRIC_NAME_SUFFIXES.items():
            metric_name = re.compile(pattern).sub(repl, metric_name)

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.normalize(metric_name.lower()),
            metric_prefix=metric_prefix,
            metric_suffix=metric_suffix,
        )
