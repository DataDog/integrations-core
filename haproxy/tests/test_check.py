# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common

pytestmark = [common.requires_new_environment, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, dd_run_check, check, prometheus_metrics):
    dd_run_check(check(common.INSTANCE))

    for metric in prometheus_metrics:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()
