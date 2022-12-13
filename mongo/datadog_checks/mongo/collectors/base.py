import re

from six import PY3, iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES

if PY3:
    long = int


class MongoCollector(object):
    """The base collector object, can be considered abstract.
    Used by the mongo check to collect and submit metric of a certain type."""

    def __init__(self, check, tags):
        """
        :param check: An instance of the mongo check class. Required to access specific properties and methods exposed
                      by the AgentCheck based class.
        :param tags: Base tags that the collector will use.
        """
        self.check = check
        self.log = self.check.log
        self.gauge = self.check.gauge
        self.base_tags = tags
        self.metrics_to_collect = self.check.metrics_to_collect

    def collect(self, api):
        """The main method exposed by the collector classes, needs to be implemented by every subclass.
        Performs the actual collection and submission of the metrics."""
        raise NotImplementedError()

    def compatible_with(self, deployment):
        """Whether or not this specific collector is compatible with this specific deployment type."""
        raise NotImplementedError()

    def _normalize(self, metric_name, submit_method, prefix=None):
        """Replace case-sensitive metric name characters, normalize the metric name,
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
        """Common utility method used to submit a pre-formatted payload to Datadog. The format is standard throughout
        this integration, each numerical value in the payload comes from nested dictionary keys. The corresponding
        metric name is the concatenation of all keys leading to a value, joined by 'dots'.

        For example, the following payload:
        {
            "db": {
                "foo": 2,
                "bar": {
                    "baz": 3
                }
            }
        }
        produces two metrics, db.foo with value 2 and db.bar.baz with value 3.

        :param payload: The nested payload described earlier.
        :param additional_tags: Additional tags to submit along self.base_tags
        :param metrics_to_collect: All the valid metric names that can be collected with its submission type.
        :param prefix: A prefix to add to all metrics
        """
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
                metrics_to_collect[metric_name][0]
                if isinstance(metrics_to_collect[metric_name], tuple)
                else metrics_to_collect[metric_name]
            )
            metric_name_alias = (
                metrics_to_collect[metric_name][1]
                if isinstance(metrics_to_collect[metric_name], tuple)
                else metric_name
            )

            # This is because https://datadoghq.atlassian.net/browse/AGENT-9001
            # Delete this code when the metrics are definitely deprecated
            if metric_name_alias in (
                'opLatencies.reads.latency',
                'opLatencies.writes.latency',
                'opLatencies.commands.latency',
            ):
                deprecated_metric_name_alias = self._normalize(metric_name_alias, AgentCheck.rate, prefix)
                AgentCheck.rate(self.check, deprecated_metric_name_alias, value, tags=tags)

            metric_name_alias = self._normalize(metric_name_alias, submit_method, prefix)
            submit_method(self.check, metric_name_alias, value, tags=tags)
            if metric_name_alias.endswith("countps"):
                # Keep old incorrect metric name (only 'top' metrics are affected)
                self.gauge(metric_name_alias[:-2], value, tags=tags)
