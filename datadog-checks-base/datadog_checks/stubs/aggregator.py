# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict, namedtuple

MetricStub = namedtuple('MetricStub', 'name type value tags hostname')


class AggregatorStub(object):
    """
    Mainly used for unit testing checks, this stub makes possible to execute
    a check without a running Agent.
    """
    # Replicate the Enum we have on the Agent
    GAUGE, RATE, COUNT, MONOTONIC_COUNT, COUNTER, HISTOGRAM, HISTORATE = range(7)

    def __init__(self):
        self.reset()

    def submit_metric(self, check, check_id, mtype, name, value, tags, hostname):
        self._metrics[name].append(MetricStub(name, mtype, value, tags, hostname))

    def submit_service_check(self, *args, **kwargs):
        pass

    def submit_event(self, *args, **kwargs):
        pass

    def metrics(self, name):
        """
        Return the metrics received under the given name
        """
        return self._metrics.get(name, [])

    def assert_metric(self, name, value=None, tags=None, count=None, at_least=1,
                      hostname=None, metric_type=None):
        """
        Assert a metric was processed by this stub
        """
        self._asserted.add(name)

        candidates = []
        for metric in self._metrics.get(name):
            if value is not None and value != metric.value:
                continue

            if tags and sorted(tags) != sorted(metric.tags):
                continue

            if hostname and hostname != metric.hostname:
                continue

            if metric_type is not None and metric_type != metric.type:
                continue

            candidates.append(metric)

        if count is not None:
            msg = "Needed exactly {} candidates for '{}', got {}".format(count, name, len(candidates))
            assert len(candidates) == count, msg
        else:
            msg = "Needed at least {} candidates for '{}', got {}".format(at_least, name, len(candidates))
            assert len(candidates) >= at_least, msg

    def reset(self):
        """
        Set the stub to its initial state
        """
        self._metrics = defaultdict(list)
        self._asserted = set()

    @property
    def metrics_asserted_pct(self):
        """
        Return the metrics assertion coverage
        """
        return len(self._asserted) / len(self._metrics) * 100.0

    @property
    def metric_names(self):
        """
        Return all the metric names we've seen so far
        """
        return self._metrics.keys()


# Use the stub as a singleton
aggregator = AggregatorStub()
