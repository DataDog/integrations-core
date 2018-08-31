# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
from six import itervalues

from datadog_checks.cockroachdb import CockroachdbCheck
from datadog_checks.cockroachdb.metrics import METRIC_MAP


def test_check(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])
    check.check(instance)

    for metric in itervalues(METRIC_MAP):
        try:
            aggregator.assert_metric(metric)
        except AssertionError:
            pass

    assert aggregator.metrics_asserted_pct > 80


def test_service_check_disk_space_ok(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])

    capacity_total = 100
    capacity_available = int(instance['disk_space_warning']) + 1

    # Keep a reference for use during mock
    track_metric = CockroachdbCheck.track_metric

    def mock_track_metric(self, metric, scraper_config):
        if metric.name == 'capacity':
            metric.samples = [('capacity', {}, capacity_total)]
        elif metric.name == 'capacity_available':
            metric.samples = [('capacity_available', {}, capacity_available)]

        return track_metric(self, metric, scraper_config)

    with mock.patch(
        'datadog_checks.cockroachdb.cockroachdb.CockroachdbCheck.track_metric',
        side_effect=mock_track_metric,
        autospec=True
    ):
        check.check(instance)

    aggregator.assert_service_check(
        CockroachdbCheck.SERVICE_CHECK_DISK_SPACE,
        status=CockroachdbCheck.OK,
        count=1
    )


def test_service_check_disk_space_warning(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])

    capacity_total = 100
    capacity_available = int(instance['disk_space_warning'])

    # Keep a reference for use during mock
    track_metric = CockroachdbCheck.track_metric

    def mock_track_metric(self, metric, scraper_config):
        if metric.name == 'capacity':
            metric.samples = [('capacity', {}, capacity_total)]
        elif metric.name == 'capacity_available':
            metric.samples = [('capacity_available', {}, capacity_available)]

        return track_metric(self, metric, scraper_config)

    with mock.patch(
        'datadog_checks.cockroachdb.cockroachdb.CockroachdbCheck.track_metric',
        side_effect=mock_track_metric,
        autospec=True
    ):
        check.check(instance)

    aggregator.assert_service_check(
        CockroachdbCheck.SERVICE_CHECK_DISK_SPACE,
        status=CockroachdbCheck.WARNING,
        count=1
    )


def test_service_check_disk_space_critical(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])

    capacity_total = 100
    capacity_available = int(instance['disk_space_critical'])

    # Keep a reference for use during mock
    track_metric = CockroachdbCheck.track_metric

    def mock_track_metric(self, metric, scraper_config):
        if metric.name == 'capacity':
            metric.samples = [('capacity', {}, capacity_total)]
        elif metric.name == 'capacity_available':
            metric.samples = [('capacity_available', {}, capacity_available)]

        return track_metric(self, metric, scraper_config)

    with mock.patch(
        'datadog_checks.cockroachdb.cockroachdb.CockroachdbCheck.track_metric',
        side_effect=mock_track_metric,
        autospec=True
    ):
        check.check(instance)

    aggregator.assert_service_check(
        CockroachdbCheck.SERVICE_CHECK_DISK_SPACE,
        status=CockroachdbCheck.CRITICAL,
        count=1
    )


def test_service_check_sql_execute_ok(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])

    # Keep a reference for use during mock
    track_metric = CockroachdbCheck.track_metric

    def mock_track_metric(self, metric, scraper_config):
        if metric.name == 'sql_conns':
            metric.samples = [('sql_conns', {}, 1)]
        elif metric.name == 'sql_query_count':
            metric.samples = [('sql_query_count', {}, 1)]

        return track_metric(self, metric, scraper_config)

    with mock.patch(
        'datadog_checks.cockroachdb.cockroachdb.CockroachdbCheck.track_metric',
        side_effect=mock_track_metric,
        autospec=True
    ):
        check.check(instance)

    aggregator.assert_service_check(
        CockroachdbCheck.SERVICE_CHECK_SQL_EXECUTE,
        status=CockroachdbCheck.OK,
        count=1
    )


def test_service_check_sql_execute_critical(aggregator, instance):
    check = CockroachdbCheck('cockroachdb', {}, {}, [instance])

    # Keep a reference for use during mock
    track_metric = CockroachdbCheck.track_metric

    def mock_track_metric(self, metric, scraper_config):
        if metric.name == 'sql_conns':
            metric.samples = [('sql_conns', {}, 1)]
        elif metric.name == 'sql_query_count':
            metric.samples = [('sql_query_count', {}, 0)]

        return track_metric(self, metric, scraper_config)

    with mock.patch(
        'datadog_checks.cockroachdb.cockroachdb.CockroachdbCheck.track_metric',
        side_effect=mock_track_metric,
        autospec=True
    ):
        check.check(instance)

    aggregator.assert_service_check(
        CockroachdbCheck.SERVICE_CHECK_SQL_EXECUTE,
        status=CockroachdbCheck.CRITICAL,
        count=1
    )
