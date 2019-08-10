# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev import EnvVars


def test_gauge(aggregator):
    c = AgentCheck()

    c.gauge("my.gauge_one", 10, tags=['foo1'])
    c.gauge("my.gauge_two", 20, tags=['foo2'])
    c.gauge("my.gauge_three", 30, tags=['foo3'])

    aggregator.assert_metric("my.gauge_one", metric_type=aggregator.GAUGE, value=10, tags=['foo1'])
    aggregator.assert_metric("my.gauge_two", metric_type=aggregator.GAUGE, value=20, tags=['foo2'])
    aggregator.assert_metric("my.gauge_three", metric_type=aggregator.GAUGE, value=30, tags=['foo3'])
    aggregator.assert_all_metrics_covered()


def test_rate_unit(aggregator):
    c = AgentCheck()

    c.rate("my.gauge_one", 10, tags=['foo1'])
    c.rate("my.gauge_two", 20, tags=['foo2'])
    c.rate("my.gauge_three", 30, tags=['foo3'])

    aggregator.assert_metric("my.gauge_one", metric_type=aggregator.RATE, value=10, tags=['foo1'])
    aggregator.assert_metric("my.gauge_two", metric_type=aggregator.RATE, value=20, tags=['foo2'])
    aggregator.assert_metric("my.gauge_three", metric_type=aggregator.RATE, value=30, tags=['foo3'])
    aggregator.assert_all_metrics_covered()


def test_rate_e2e_metric_type(aggregator):
    with EnvVars({'DDEV_E2E_PYTHON_PATH': 'true'}):
        c = AgentCheck()

        # In e2e, submission type rate is converted to gauge
        # below we simulate the check c.gauge() from e2e agent check data
        c.gauge("my.gauge_one", value=1, tags=['foo1'])
        c.gauge("my.gauge_two", value=1, tags=['foo2'])

        aggregator.assert_metric("my.gauge_one", metric_type=aggregator.RATE, tags=['foo1'])
        aggregator.assert_metric("my.gauge_two", metric_type=aggregator.RATE, tags=['foo2'])
        aggregator.assert_all_metrics_covered()


def test_e2e_count_success(aggregator):
    with EnvVars({'DDEV_E2E_PYTHON_PATH': 'true'}):
        c = AgentCheck()

        # In e2e, submission type rate is converted to gauge
        # below we simulate the check c.gauge() from e2e agent check data
        c.gauge("my.gauge_one", value=1, tags=['foo1'])
        c.gauge("my.gauge_two", value=1, tags=['foo2'])
        c.gauge("my.gauge_tree", value=1, tags=['foo2'])

        aggregator.assert_metric("my.gauge_one", count=2, metric_type=aggregator.RATE, tags=['foo1'])
        aggregator.assert_metric("my.gauge_two", count=2, metric_type=aggregator.RATE, tags=['foo2'])
        aggregator.assert_metric("my.gauge_tree", count=1, metric_type=aggregator.GAUGE, tags=['foo2'])
        aggregator.assert_all_metrics_covered()


def test_e2e_count_without_metric_type(aggregator):
    with EnvVars({'DDEV_E2E_PYTHON_PATH': 'true'}):
        c = AgentCheck()

        c.gauge("my.gauge_one", value=1)

        with pytest.raises(Exception):
            aggregator.assert_metric("my.gauge_one", count=2)
