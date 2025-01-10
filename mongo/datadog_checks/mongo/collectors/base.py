# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
import time
from functools import wraps

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES


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
        self._collection_interval = None
        self._collector_key = (self.__class__.__name__,)
        self._system_collections_skip_stats = {
            "local": frozenset(["system.replset", "replset.election", "replset.minvalid"])
        }

    def collect(self, api):
        """The main method exposed by the collector classes, needs to be implemented by every subclass.
        Performs the actual collection and submission of the metrics."""
        raise NotImplementedError()

    def compatible_with(self, deployment):
        """Whether or not this specific collector is compatible with this specific deployment type."""
        raise NotImplementedError()

    def should_skip_system_collection(self, coll_name):
        """Whether or not the collection should be skipped because collStats or indexStats
        is not authorized to run on certain system collections.
        """
        db_name = getattr(self, "db_name", None)
        if not db_name or db_name not in self._system_collections_skip_stats:
            return False
        return coll_name in self._system_collections_skip_stats[db_name]

    def _normalize(self, metric_name, submit_method, prefix=None):
        """Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "mongodb." if not prefix else "mongodb.{0}.".format(prefix)
        metric_suffix = "ps" if submit_method == AgentCheck.rate else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in CASE_SENSITIVE_METRIC_NAME_SUFFIXES.items():
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
            if not isinstance(value, (int, float)):
                raise TypeError(
                    u"{0} value is a {1}, it should be an int, or a float instead.".format(metric_name, type(value))
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
            if (
                metric_name_alias.endswith("countps")
                or metric_name_alias.endswith("accesses.opsps")
                or metric_name_alias.endswith("collectionscans.totalps")
                or metric_name_alias.endswith("collectionscans.nontailableps")
            ):
                # Keep old incorrect metric name
                # 'top' and 'index', 'collectionscans' metrics are affected
                self.gauge(metric_name_alias[:-2], value, tags=tags)

    def get_last_collection_timestamp(self):
        return self.check.metrics_last_collection_timestamp.get(self._collector_key)

    def set_last_collection_timestamp(self, timestamp):
        self.check.metrics_last_collection_timestamp[self._collector_key] = timestamp


def collection_interval_checker(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        current_time = time.time()
        # If _collection_interval not set or set to the check default, call the function to collect the metrics
        if (
            self._collection_interval is None
            or self._collection_interval <= self.check._config.min_collection_interval  # Ensure the interval is valid
        ):
            self.set_last_collection_timestamp(current_time)
            return func(self, *args, **kwargs)

        # Check if enough time has passed since the last collection
        last_collection_timestamp = self.get_last_collection_timestamp()
        if not last_collection_timestamp or current_time - last_collection_timestamp >= self._collection_interval:
            self.set_last_collection_timestamp(current_time)
            return func(self, *args, **kwargs)
        else:
            self.log.debug("%s skipped: collection interval not reached yet.", self.__class__.__name__)

    return wrapper
