# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import json
import os
import re
from collections import OrderedDict, defaultdict

from six import iteritems

from ..constants import ServiceCheck
from ..utils.common import ensure_unicode, to_native_string
from .common import HistogramBucketStub, MetricStub, ServiceCheckStub
from .similar import build_similar_elements_msg

METRIC_REPLACEMENT = re.compile(r"([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)")
METRIC_DOTUNDERSCORE_CLEANUP = re.compile(r"_*\._*")


def normalize_tags(tags, sort=False):
    # The base class ensures the Agent receives bytes in PY2 and unicode in PY3.
    # This function makes sure strings are compared with the same type.
    if tags:
        if sort:
            return sorted(to_native_string(tag) for tag in tags)
        else:
            return [to_native_string(tag) for tag in tags]
    return tags


def backend_normalize_metric_name(metric_name):
    """
    Normalize a metric name for the backend to understand it.
    This is the same metric that is used to validate the metadata.csv file
    """
    metric_name = METRIC_REPLACEMENT.sub("_", metric_name)
    return METRIC_DOTUNDERSCORE_CLEANUP.sub(".", metric_name).strip("_")


def check_tag_names(metric, tags):
    if not os.environ.get('DDEV_SKIP_GENERIC_TAGS_CHECK'):
        try:
            from datadog_checks.base.utils.tagging import GENERIC_TAGS
        except ImportError:
            GENERIC_TAGS = []

        for tag in tags:
            tag_name = tag.split(':')[0]
            if tag_name in GENERIC_TAGS:
                raise Exception(
                    "Metric {} was submitted with a forbidden tag: {}. Please rename this tag, or skip "
                    "the tag validation with DDEV_SKIP_GENERIC_TAGS_CHECK environment variable.".format(
                        metric, tag_name
                    )
                )


class AggregatorStub(object):
    """
    This implements the methods defined by the Agent's
    [C bindings](https://github.com/DataDog/datadog-agent/blob/master/rtloader/common/builtins/aggregator.c)
    which in turn call the
    [Go backend](https://github.com/DataDog/datadog-agent/blob/master/pkg/collector/python/aggregator.go).

    It also provides utility methods for test assertions.
    """

    # Replicate the Enum we have on the Agent
    METRIC_ENUM_MAP = OrderedDict(
        (
            ('gauge', 0),
            ('rate', 1),
            ('count', 2),
            ('monotonic_count', 3),
            ('counter', 4),
            ('histogram', 5),
            ('historate', 6),
        )
    )
    METRIC_ENUM_MAP_REV = {v: k for k, v in iteritems(METRIC_ENUM_MAP)}
    GAUGE, RATE, COUNT, MONOTONIC_COUNT, COUNTER, HISTOGRAM, HISTORATE = list(METRIC_ENUM_MAP.values())
    AGGREGATE_TYPES = {COUNT, COUNTER}
    IGNORED_METRICS = {'datadog.agent.profile.memory.check_run_alloc'}
    METRIC_TYPE_SUBMISSION_TO_BACKEND_MAP = {
        'gauge': 'gauge',
        'rate': 'gauge',
        'count': 'count',
        'monotonic_count': 'count',
        'counter': 'rate',
        'histogram': 'rate',  # Checking .count only, the other are gauges
        'historate': 'rate',  # Checking .count only, the other are gauges
    }

    def __init__(self):
        self._metrics = defaultdict(list)
        self._asserted = set()
        self._service_checks = defaultdict(list)
        self._events = []
        # dict[event_type, [events]]
        self._event_platform_events = {}
        self._histogram_buckets = defaultdict(list)

    @classmethod
    def is_aggregate(cls, mtype):
        return mtype in cls.AGGREGATE_TYPES

    @classmethod
    def ignore_metric(cls, name):
        return name in cls.IGNORED_METRICS

    def submit_metric(self, check, check_id, mtype, name, value, tags, hostname, flush_first_value):
        check_tag_names(name, tags)
        if not self.ignore_metric(name):
            self._metrics[name].append(MetricStub(name, mtype, value, tags, hostname, None))

    def submit_metric_e2e(
        self, check, check_id, mtype, name, value, tags, hostname, device=None, flush_first_value=False
    ):
        check_tag_names(name, tags)
        # Device is only present in metrics read from the real agent in e2e tests. Normally it is submitted as a tag
        if not self.ignore_metric(name):
            self._metrics[name].append(MetricStub(name, mtype, value, tags, hostname, device))

    def submit_service_check(self, check, check_id, name, status, tags, hostname, message):
        if status == ServiceCheck.OK and message:
            raise Exception("Expected empty message on OK service check")

        check_tag_names(name, tags)
        self._service_checks[name].append(ServiceCheckStub(check_id, name, status, tags, hostname, message))

    def submit_event(self, check, check_id, event):
        self._events.append(event)

    def submit_event_platform_event(self, check, check_id, raw_event, event_type):
        self._event_platform_events[event_type].append(raw_event)

    def submit_histogram_bucket(
        self, check, check_id, name, value, lower_bound, upper_bound, monotonic, hostname, tags, flush_first_value=False
    ):
        check_tag_names(name, tags)
        self._histogram_buckets[name].append(
            HistogramBucketStub(name, value, lower_bound, upper_bound, monotonic, hostname, tags)
        )

    def metrics(self, name):
        """
        Return the metrics received under the given name
        """
        return [
            MetricStub(
                ensure_unicode(stub.name),
                stub.type,
                stub.value,
                normalize_tags(stub.tags),
                ensure_unicode(stub.hostname),
                stub.device,
            )
            for stub in self._metrics.get(to_native_string(name), [])
        ]

    def service_checks(self, name):
        """
        Return the service checks received under the given name
        """
        return [
            ServiceCheckStub(
                ensure_unicode(stub.check_id),
                ensure_unicode(stub.name),
                stub.status,
                normalize_tags(stub.tags),
                ensure_unicode(stub.hostname),
                ensure_unicode(stub.message),
            )
            for stub in self._service_checks.get(to_native_string(name), [])
        ]

    @property
    def events(self):
        """
        Return all events
        """
        return self._events

    def get_event_platform_events(self, event_type, parse_json=True):
        """
        Return all event platform events for the event_type
        """
        return [json.loads(e) if parse_json else e for e in self._event_platform_events[event_type]]

    def histogram_bucket(self, name):
        """
        Return the histogram buckets received under the given name
        """
        return [
            HistogramBucketStub(
                ensure_unicode(stub.name),
                stub.value,
                stub.lower_bound,
                stub.upper_bound,
                stub.monotonic,
                ensure_unicode(stub.hostname),
                normalize_tags(stub.tags),
            )
            for stub in self._histogram_buckets.get(to_native_string(name), [])
        ]

    def assert_metric_has_tag(self, metric_name, tag, count=None, at_least=1):
        """
        Assert a metric is tagged with tag
        """
        self._asserted.add(metric_name)

        candidates = []
        for metric in self.metrics(metric_name):
            if tag in metric.tags:
                candidates.append(metric)

        msg = "Candidates size assertion for `{}`, count: {}, at_least: {}) failed".format(metric_name, count, at_least)
        if count is not None:
            assert len(candidates) == count, msg
        else:
            assert len(candidates) >= at_least, msg

    # Potential kwargs: aggregation_key, alert_type, event_type,
    # msg_title, source_type_name
    def assert_event(self, msg_text, count=None, at_least=1, exact_match=True, tags=None, **kwargs):
        candidates = []
        for e in self.events:
            if exact_match and msg_text != e['msg_text'] or msg_text not in e['msg_text']:
                continue
            if tags and set(tags) != set(e['tags']):
                continue
            for name, value in iteritems(kwargs):
                if e[name] != value:
                    break
            else:
                candidates.append(e)

        msg = "Candidates size assertion for `{}`, count: {}, at_least: {}) failed".format(msg_text, count, at_least)
        if count is not None:
            assert len(candidates) == count, msg
        else:
            assert len(candidates) >= at_least, msg

    def assert_histogram_bucket(
        self, name, value, lower_bound, upper_bound, monotonic, hostname, tags, count=None, at_least=1
    ):
        expected_tags = normalize_tags(tags, sort=True)

        candidates = []
        for bucket in self.histogram_bucket(name):
            if value is not None and value != bucket.value:
                continue

            if expected_tags and expected_tags != sorted(bucket.tags):
                continue

            if hostname and hostname != bucket.hostname:
                continue

            if monotonic != bucket.monotonic:
                continue

            candidates.append(bucket)

        expected_bucket = HistogramBucketStub(name, value, lower_bound, upper_bound, monotonic, hostname, tags)

        if count is not None:
            msg = "Needed exactly {} candidates for '{}', got {}".format(count, name, len(candidates))
            condition = len(candidates) == count
        else:
            msg = "Needed at least {} candidates for '{}', got {}".format(at_least, name, len(candidates))
            condition = len(candidates) >= at_least
        self._assert(
            condition=condition, msg=msg, expected_stub=expected_bucket, submitted_elements=self._histogram_buckets
        )

    def assert_metric(
        self, name, value=None, tags=None, count=None, at_least=1, hostname=None, metric_type=None, device=None
    ):
        """
        Assert a metric was processed by this stub
        """

        self._asserted.add(name)
        expected_tags = normalize_tags(tags, sort=True)

        candidates = []
        for metric in self.metrics(name):
            if value is not None and not self.is_aggregate(metric.type) and value != metric.value:
                continue

            if expected_tags and expected_tags != sorted(metric.tags):
                continue

            if hostname is not None and hostname != metric.hostname:
                continue

            if metric_type is not None and metric_type != metric.type:
                continue

            if device is not None and device != metric.device:
                continue

            candidates.append(metric)

        expected_metric = MetricStub(name, metric_type, value, tags, hostname, device)

        if value is not None and candidates and all(self.is_aggregate(m.type) for m in candidates):
            got = sum(m.value for m in candidates)
            msg = "Expected count value for '{}': {}, got {}".format(name, value, got)
            condition = value == got
        elif count is not None:
            msg = "Needed exactly {} candidates for '{}', got {}".format(count, name, len(candidates))
            condition = len(candidates) == count
        else:
            msg = "Needed at least {} candidates for '{}', got {}".format(at_least, name, len(candidates))
            condition = len(candidates) >= at_least
        self._assert(condition, msg=msg, expected_stub=expected_metric, submitted_elements=self._metrics)

    def assert_service_check(self, name, status=None, tags=None, count=None, at_least=1, hostname=None, message=None):
        """
        Assert a service check was processed by this stub
        """
        tags = normalize_tags(tags, sort=True)
        candidates = []
        for sc in self.service_checks(name):
            if status is not None and status != sc.status:
                continue

            if tags and tags != sorted(sc.tags):
                continue

            if hostname is not None and hostname != sc.hostname:
                continue

            if message is not None and message != sc.message:
                continue

            candidates.append(sc)

        expected_service_check = ServiceCheckStub(
            None, name=name, status=status, tags=tags, hostname=hostname, message=message
        )

        if count is not None:
            msg = "Needed exactly {} candidates for '{}', got {}".format(count, name, len(candidates))
            condition = len(candidates) == count
        else:
            msg = "Needed at least {} candidates for '{}', got {}".format(at_least, name, len(candidates))
            condition = len(candidates) >= at_least
        self._assert(
            condition=condition, msg=msg, expected_stub=expected_service_check, submitted_elements=self._service_checks
        )

    @staticmethod
    def _assert(condition, msg, expected_stub, submitted_elements):
        new_msg = msg
        if not condition:  # It's costly to build the message with similar metrics, so it's built only on failure.
            new_msg = "{}\n{}".format(msg, build_similar_elements_msg(expected_stub, submitted_elements))
        assert condition, new_msg

    def assert_all_metrics_covered(self):
        # use `condition` to avoid building the `msg` if not needed
        condition = self.metrics_asserted_pct >= 100.0
        msg = ''
        if not condition:
            prefix = '\n\t- '
            msg = 'Some metrics are missing:'
            msg += '\nAsserted Metrics:{}{}'.format(prefix, prefix.join(sorted(self._asserted)))
            msg += '\nMissing Metrics:{}{}'.format(prefix, prefix.join(sorted(self.not_asserted())))
        assert condition, msg

    def assert_metrics_using_metadata(
        self, metadata_metrics, check_metric_type=True, check_submission_type=False, exclude=None
    ):
        """
        Assert metrics using metadata.csv

        Checking type: By default we are asserting the in-app metric type (`check_submission_type=False`),
        asserting this type make sense for e2e (metrics collected from agent).
        For integrations tests, we can check the submission type with `check_submission_type=True`, or
        use `check_metric_type=False` not to check types.

        Usage:

            from datadog_checks.dev.utils import get_metadata_metrics
            aggregator.assert_metrics_using_metadata(get_metadata_metrics())

        """

        exclude = exclude or []
        errors = set()
        for metric_name, metric_stubs in iteritems(self._metrics):
            if metric_name in exclude:
                continue
            for metric_stub in metric_stubs:
                metric_stub_name = backend_normalize_metric_name(metric_stub.name)
                actual_metric_type = AggregatorStub.METRIC_ENUM_MAP_REV[metric_stub.type]

                # We only check `*.count` metrics for histogram and historate submissions
                # Note: all Openmetrics histogram and summary metrics are actually separately submitted
                if check_submission_type and actual_metric_type in ['histogram', 'historate']:
                    metric_stub_name += '.count'

                # Checking the metric is in `metadata.csv`
                if metric_stub_name not in metadata_metrics:
                    errors.add("Expect `{}` to be in metadata.csv.".format(metric_stub_name))
                    continue

                expected_metric_type = metadata_metrics[metric_stub_name]['metric_type']
                if check_submission_type:
                    # Integration tests type mapping
                    actual_metric_type = AggregatorStub.METRIC_TYPE_SUBMISSION_TO_BACKEND_MAP[actual_metric_type]
                else:
                    # E2E tests
                    if actual_metric_type == 'monotonic_count' and expected_metric_type == 'count':
                        actual_metric_type = 'count'

                if check_metric_type:
                    if expected_metric_type != actual_metric_type:
                        errors.add(
                            "Expect `{}` to have type `{}` but got `{}`.".format(
                                metric_stub_name, expected_metric_type, actual_metric_type
                            )
                        )

        assert not errors, "Metadata assertion errors using metadata.csv:" + "\n\t- ".join([''] + sorted(errors))

    def assert_no_duplicate_all(self):
        """
        Assert no duplicate metrics and service checks have been submitted.
        """
        self.assert_no_duplicate_metrics()
        self.assert_no_duplicate_service_checks()

    def assert_no_duplicate_metrics(self):
        """
        Assert no duplicate metrics have been submitted.

        Metrics are considered duplicate when all following fields match:

        - metric name
        - type (gauge, rate, etc)
        - tags
        - hostname
        """
        # metric types that intended to be called multiple times are ignored
        ignored_types = [self.COUNT, self.COUNTER]
        metric_stubs = [m for metrics in self._metrics.values() for m in metrics if m.type not in ignored_types]

        def stub_to_key_fn(stub):
            return stub.name, stub.type, str(sorted(stub.tags)), stub.hostname

        self._assert_no_duplicate_stub('metric', metric_stubs, stub_to_key_fn)

    def assert_no_duplicate_service_checks(self):
        """
        Assert no duplicate service checks have been submitted.

        Service checks are considered duplicate when all following fields match:
            - metric name
            - status
            - tags
            - hostname
        """
        service_check_stubs = [m for metrics in self._service_checks.values() for m in metrics]

        def stub_to_key_fn(stub):
            return stub.name, stub.status, str(sorted(stub.tags)), stub.hostname

        self._assert_no_duplicate_stub('service_check', service_check_stubs, stub_to_key_fn)

    @staticmethod
    def _assert_no_duplicate_stub(stub_type, all_metrics, stub_to_key_fn):
        all_contexts = defaultdict(list)
        for metric in all_metrics:
            context = stub_to_key_fn(metric)
            all_contexts[context].append(metric)

        dup_contexts = defaultdict(list)
        for context, metrics in iteritems(all_contexts):
            if len(metrics) > 1:
                dup_contexts[context] = metrics

        err_msg_lines = ["Duplicate {}s found:".format(stub_type)]
        for key in sorted(dup_contexts):
            contexts = dup_contexts[key]
            err_msg_lines.append('- {}'.format(contexts[0].name))
            for metric in contexts:
                err_msg_lines.append('    ' + str(metric))

        assert len(dup_contexts) == 0, "\n".join(err_msg_lines)

    def reset(self):
        """
        Set the stub to its initial state
        """
        self._metrics = defaultdict(list)
        self._asserted = set()
        self._service_checks = defaultdict(list)
        self._events = []
        self._event_platform_events = defaultdict(list)

    def all_metrics_asserted(self):
        assert self.metrics_asserted_pct >= 100.0

    def not_asserted(self):
        present_metrics = {ensure_unicode(m) for m in self._metrics}
        return present_metrics - set(self._asserted)

    def assert_metric_has_tag_prefix(self, metric_name, tag_prefix, count=None, at_least=1):
        candidates = []
        self._asserted.add(metric_name)

        for metric in self.metrics(metric_name):
            tags = metric.tags
            gtags = [t for t in tags if t.startswith(tag_prefix)]
            if len(gtags) > 0:
                candidates.append(metric)

        msg = "Candidates size assertion for `{}`, count: {}, at_least: {}) failed".format(metric_name, count, at_least)
        if count is not None:
            assert len(candidates) == count, msg
        else:
            assert len(candidates) >= at_least, msg

    @property
    def metrics_asserted_pct(self):
        """
        Return the metrics assertion coverage
        """
        num_metrics = len(self._metrics)
        num_asserted = len(self._asserted)

        if num_metrics == 0:
            if num_asserted == 0:
                return 100
            else:
                return 0

        # If it there have been assertions with at_least=0 the length of the num_metrics and num_asserted can match
        # even if there are different metrics in each set
        not_asserted = self.not_asserted()
        return (num_metrics - len(not_asserted)) / num_metrics * 100

    @property
    def metric_names(self):
        """
        Return all the metric names we've seen so far
        """
        return [ensure_unicode(name) for name in self._metrics.keys()]

    @property
    def service_check_names(self):
        """
        Return all the service checks names seen so far
        """
        return [ensure_unicode(name) for name in self._service_checks.keys()]


# Use the stub as a singleton
aggregator = AggregatorStub()
