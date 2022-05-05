# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
from contextlib import contextmanager

from ..agent.common import METRIC_NAMESPACE_METRICS

try:
    from sys import intern as cached_string

# TODO: remove when we drop Python 2
except ImportError:

    def cached_string(s):
        return s


class MetricLimiter(object):
    DEFAULT_LIMIT_NAMES = 1000
    DEFAULT_LIMIT_TAG_SETS = 10000

    def __init__(self, check):
        self.check = check

        instance = check.instance or {}
        metric_limits = instance.get('metric_limits', {})
        self.persist = metric_limits.get('persist', True)
        self.name_limit = int(metric_limits.get('names', check.METRIC_LIMIT_NAMES))
        if 'max_returned_metrics' in instance:
            self.tag_set_limit = int(instance['max_returned_metrics'])
            check.log.warning('Setting `max_returned_metrics` is deprecated, use `metric_limits.tag_sets`')
        else:
            self.tag_set_limit = int(metric_limits.get('tag_sets', check.METRIC_LIMIT_TAG_SETS))

        if self.name_limit <= 0:
            check.log.warning(
                'Setting `metric_limits.names` to zero is not allowed. Reverting to the default metric name limit: %s',
                check.METRIC_LIMIT_NAMES,
            )
        if self.tag_set_limit <= 0:
            check.log.warning(
                'Setting `metric_limits.tag_sets` to zero is not allowed. Reverting to the default tag set limit: %s',
                check.METRIC_LIMIT_TAG_SETS,
            )

        # {
        #     'hostname1': {  # will be just one (empty string) most of the time
        #         'metric1': {
        #             6192391042392776118,  # hash(frozenset(['foo:bar', 'bar:baz']))
        #             ...
        #         },
        #         ...
        #     },
        #     ...
        # }
        self.cache = defaultdict(lambda: defaultdict(lambda: set()))

        self.debugging = check.debug_metrics.get('metric_limits', False)
        # For bypassing limits to send debug metrics
        self.disabled = False

        # Only warn once per host per check run
        self.name_limit_reached = defaultdict(lambda: False)
        self.tag_set_limit_reached = defaultdict(lambda: set())

    def is_reached(self, hostname, metric_name, tags):
        if self.disabled:
            return False

        limited = False
        hostname = cached_string(hostname)
        metrics = self.cache[hostname]
        if len(metrics) >= self.name_limit:
            limited = True
            if not self.name_limit_reached[hostname]:
                self.check.warning(
                    'Check `%s` instance `%s` on host `%s` has reached the limit of unique metric names',
                    self.check.name,
                    self.check.check_id,
                    hostname if hostname else self.check.hostname,
                )
                self.name_limit_reached[hostname] = True

        metric_name = cached_string(metric_name)
        tag_sets = metrics[metric_name]
        if len(tag_sets) >= self.tag_set_limit:
            limited = True
            if metric_name not in self.tag_set_limit_reached[hostname]:
                self.check.warning(
                    'Metric `%s` for check `%s` instance `%s` on host `%s` has reached the limit of tag sets',
                    metric_name,
                    self.check.name,
                    self.check.check_id,
                    hostname if hostname else self.check.hostname,
                )
                self.tag_set_limit_reached[hostname].add(metric_name)

        if limited and not self.debugging:
            return True

        tag_sets.add(hash(frozenset(tags)))
        return limited

    def reset(self):
        self.name_limit_reached.clear()
        self.tag_set_limit_reached.clear()

        if not self.persist:
            self.cache.clear()

    def submit_debug_metrics(self):
        if not self.debugging:
            return

        with self.disable_limits():
            global_tags = self.check.get_debug_metric_tags()
            self.check.gauge(
                '{}.limits.names.total'.format(METRIC_NAMESPACE_METRICS), self.name_limit, tags=global_tags
            )
            self.check.gauge(
                '{}.limits.tag_sets.total'.format(METRIC_NAMESPACE_METRICS), self.tag_set_limit, tags=global_tags
            )

            for hostname, metrics in self.cache.items():
                self.check.gauge(
                    '{}.limits.names.current'.format(METRIC_NAMESPACE_METRICS),
                    len(metrics),
                    tags=global_tags,
                    hostname=hostname,
                )

                for metric, tag_sets in metrics.items():
                    tags = ['metric_name:{}'.format(metric)]
                    tags.extend(global_tags)
                    self.check.gauge(
                        '{}.limits.tag_sets.current'.format(METRIC_NAMESPACE_METRICS),
                        len(tag_sets),
                        tags=tags,
                        hostname=hostname,
                    )

    @contextmanager
    def disable_limits(self):
        self.disabled = True
        try:
            yield
        finally:
            self.disabled = False
