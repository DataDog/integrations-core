# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from ..utils import requires_py3
from .utils import get_check

pytestmark = [requires_py3, pytest.mark.openmetrics, pytest.mark.openmetrics_interface]


def test_default_config(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
        """
    )
    check = get_check()
    check.get_default_config = lambda: {'metrics': ['.+'], 'rename_labels': {'foo': 'bar'}}
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:baz']
    )

    aggregator.assert_all_metrics_covered()


def test_service_check_dynamic_tags(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
        # HELP state Node state
        # TYPE state gauge
        state{bar="baz"} 3
        """
    )
    check = get_check(
        {'metrics': ['.+', {'state': {'type': 'service_check', 'status_map': {'3': 'ok'}}}], 'tags': ['foo:bar']}
    )
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes',
        6396288,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'foo:bar', 'foo:baz'],
    )
    aggregator.assert_service_check('test.state', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])
    aggregator.assert_service_check('test.openmetrics.health', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_check_names) == 2

    aggregator.reset()
    check.set_dynamic_tags('baz:foo')
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes',
        6396288,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'foo:bar', 'foo:baz', 'baz:foo'],
    )
    aggregator.assert_service_check('test.state', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])
    aggregator.assert_service_check('test.openmetrics.health', ServiceCheck.OK, tags=['endpoint:test', 'foo:bar'])

    aggregator.assert_all_metrics_covered()
    assert len(aggregator.service_check_names) == 2


def test_scraper_override(aggregator, dd_run_check, mock_http_response):
    # TODO: when we drop Python 2 move this up top
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="baz"} 6.396288e+06
        """
    )
    check = get_check({'metrics': ['.+']})
    check.create_scraper = lambda config: OpenMetricsCompatibilityScraper(check, check.get_config_with_defaults(config))
    dd_run_check(check)

    aggregator.assert_service_check('test.prometheus.health', ServiceCheck.OK, tags=['endpoint:test'])
