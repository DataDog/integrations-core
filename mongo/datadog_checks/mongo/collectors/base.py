import re

from six import PY3, iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES

if PY3:
    long = int


class MongoCollector(object):
    def __init__(self, check, db_name, tags):
        self.check = check
        self.db_name = db_name
        self.log = self.check.log
        self.gauge = self.check.gauge
        self.base_tags = tags
        self.metrics_to_collect = self.check.metrics_to_collect

    def collect(self, client):
        raise NotImplementedError()

    def _normalize(self, metric_name, submit_method, prefix=None):
        """
        Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "mongodb." if not prefix else "mongodb.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == AgentCheck.rate else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in iteritems(CASE_SENSITIVE_METRIC_NAME_SUFFIXES):
            metric_name = re.compile(pattern).sub(repl, metric_name)

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.check.normalize(metric_name.lower()),
            metric_prefix=metric_prefix,
            metric_suffix=metric_suffix,
        )

    def _submit_payload(self, payload, additional_tags=None, metrics_to_collect=None, prefix=""):
        if metrics_to_collect is None:
            metrics_to_collect = self.metrics_to_collect
        tags = self.base_tags + (additional_tags or [])
        # Go through the metrics and save the values
        for metric_name in metrics_to_collect:
            # each metric is of the form: x.y.z with z optional
            # and can be found at status[x][y][z]
            value = payload

            try:
                for c in metric_name.split("."):
                    value = value[c]
            except KeyError:
                continue

            # value is now status[x][y][z]
            if not isinstance(value, (int, long, float)):
                raise TypeError(
                    u"{0} value is a {1}, it should be an int, a float or a long instead.".format(
                        metric_name, type(value)
                    )
                )

            # Submit the metric
            submit_method = (
                self.metrics_to_collect[metric_name][0]
                if isinstance(self.metrics_to_collect[metric_name], tuple)
                else self.metrics_to_collect[metric_name]
            )
            metric_name_alias = (
                self.metrics_to_collect[metric_name][1]
                if isinstance(self.metrics_to_collect[metric_name], tuple)
                else metric_name
            )
            metric_name_alias = self._normalize(metric_name_alias, submit_method, prefix)
            submit_method(self.check, metric_name_alias, value, tags=tags)
            if metric_name_alias.endswith("countps"):
                # Keep old incorrect metric name (only 'top' metrics are affected)
                self.gauge(metric_name_alias[:-2], value, tags=tags)
