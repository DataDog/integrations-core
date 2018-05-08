# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict, namedtuple

MetricStub = namedtuple('MetricStub', 'name type value tags hostname')
ServiceCheckStub = namedtuple('ServiceCheckStub', 'check_id name status tags hostname message')


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

    def submit_service_check(self, check, check_id, name, status, tags, hostname, message):
        self._service_checks[name].append(ServiceCheckStub(check_id, name, status, tags, hostname, message))

    def submit_event(self, check, check_id, event):
        self._events.append(event)

    def metrics(self, name):
        """
        Return the metrics received under the given name
        """
        return self._metrics.get(name, [])

    def service_checks(self, name):
        """
        Return the service checks received under the given name
        """
        return self._service_checks.get(name, [])

    @property
    def events(self):
        """
        Return all events
        """
        return self._events

    def assert_metric_has_tag(self, metric_name, tag, count=None, at_least=1):
        """
        Assert a metric is tagged with tag
        """
        self._asserted.add(metric_name)

        candidates = []
        for metric in self._metrics.get(metric_name, []):
            if tag in metric.tags:
                candidates.append(metric)

        if count:
            assert len(candidates) == count
        else:
            assert len(candidates) > at_least

    def assert_metric(self, name, value=None, tags=None, count=None, at_least=1,
                      hostname=None, metric_type=None):
        """
        Assert a metric was processed by this stub
        """
        self._asserted.add(name)

        candidates = []
        for metric in self._metrics.get(name, []):
            if value is not None and metric.type != self.COUNTER and value != metric.value:
                continue

            if tags and sorted(tags) != sorted(metric.tags):
                continue

            if hostname and hostname != metric.hostname:
                continue

            if metric_type is not None and metric_type != metric.type:
                continue

            candidates.append(metric)

        if value is not None and candidates and all(m.type == self.COUNTER for m in candidates):
            got = sum(m.value for m in candidates)
            msg = "Expected count value for '{}': {}, got {}".format(name, value, got)
            assert value == got, msg

        if count is not None:
            msg = "Needed exactly {} candidates for '{}', got {}".format(count, name, len(candidates))
            assert len(candidates) == count, msg
        else:
            msg = "Needed at least {} candidates for '{}', got {}".format(at_least, name, len(candidates))
            assert len(candidates) >= at_least, msg

    def assert_service_check(self, name, status=None, tags=None, count=None, at_least=1, hostname=None):
        """
        Assert a service check was processed by this stub
        """
        candidates = []
        for sc in aggregator.service_checks(name):
            if status is not None and status != sc.status:
                continue

            if tags and sorted(tags) != sorted(sc.tags):
                continue

            candidates.append(sc)

        if count is not None:
            msg = "Needed exactly {} candidates for '{}', got {}".format(count, name, len(candidates))
            assert len(candidates) == count, msg
        else:
            msg = "Needed at least {} candidates for '{}', got {}".format(at_least, name, len(candidates))
            assert len(candidates) >= at_least, msg

    def assert_all_metrics_covered(self):
        assert aggregator.metrics_asserted_pct >= 100.0

    def reset(self):
        """
        Set the stub to its initial state
        """
        self._metrics = defaultdict(list)
        self._asserted = set()
        self._service_checks = defaultdict(list)
        self._events = []

    def all_metrics_asserted(self):
        assert aggregator.metrics_asserted_pct >= 100.0

    def not_asserted(self):
        not_asserted = []
        for mname, metric in aggregator._metrics.iteritems():
            if mname not in aggregator._asserted:
                not_asserted.append(metric)
        return not_asserted

    @property
    def metrics_asserted_pct(self):
        """
        Return the metrics assertion coverage
        """
        if len(self._metrics) == 0:
            return 100.0
        return len(self._asserted) / float(len(self._metrics)) * 100.0

    @property
    def metric_names(self):
        """
        Return all the metric names we've seen so far
        """
        return self._metrics.keys()

    @property
    def service_check_names(self):
        """
        Return all the service checks names seen so far
        """
        return self._service_checks.keys()


# Use the stub as a singleton
aggregator = AggregatorStub()
