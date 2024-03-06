# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import itervalues

from datadog_checks.cockroachdb.metrics import METRIC_MAP
from datadog_checks.dev.utils import assert_service_checks


def assert_check(aggregator):
    for metric in itervalues(METRIC_MAP):
        aggregator.assert_metric('cockroachdb.{}'.format(metric), at_least=0)

    assert aggregator.metrics_asserted_pct > 80, 'Missing metrics {}'.format(aggregator.not_asserted())

    assert_service_checks(aggregator)
