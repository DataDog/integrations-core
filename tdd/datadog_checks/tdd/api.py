import re
from abc import abstractmethod

from datadog_checks.base import AgentCheck
from datadog_checks.tdd.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES, METRICS


class Api:
    def __init__(self, check, instance):
        self._check = check
        self._log = check.log
        self._instance = instance

    @abstractmethod
    def report_service_check(self):
        pass

    @abstractmethod
    def report_metadata(self):
        pass

    @abstractmethod
    def report_metrics(self):
        pass

    def _report_json(self, json, prefix=None):
        for metric_name in METRICS:
            value = json
            try:
                for c in metric_name.split("."):
                    value = value[c]
            except KeyError:
                continue
            submit_method = METRICS[metric_name][0] if isinstance(METRICS[metric_name], tuple) else METRICS[metric_name]
            metric_name_alias = METRICS[metric_name][1] if isinstance(METRICS[metric_name], tuple) else metric_name
            metric_name_alias = self._normalize(metric_name_alias, submit_method, prefix)
            self._log.debug('%s: %s [alias: %s, method: %s]', metric_name, value, metric_name_alias, submit_method)
            submit_method(self._check, metric_name_alias, value)

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
            normalized_metric_name=self._check.normalize(metric_name.lower()),
            metric_prefix=metric_prefix,
            metric_suffix=metric_suffix,
        )
