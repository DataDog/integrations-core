# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY2

from datadog_checks.coredns import CoreDNSCheck
from datadog_checks.dev.utils import ON_WINDOWS, get_metadata_metrics

from .common import CHECK_NAME, METRICS, METRICS_V2, NAMESPACE


class TestCoreDNS:
    """Basic Test for CoreDNS integration."""

    def test_check(self, aggregator, mock_get, dd_run_check, instance):
        """
        Testing CoreDNS check.
        """

        check = CoreDNSCheck(CHECK_NAME, {}, [instance])
        dd_run_check(check)

        # check that we then get the count metrics also
        dd_run_check(check)

        # `.cache_hits_count` metric is only tested against the metrics fixtures file
        # because the metric is not available in docker/e2e.
        metrics = METRICS + [NAMESPACE + '.cache_hits_count']

        for metric in metrics:
            aggregator.assert_metric(metric)

    @pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
    def test_check_omv2(self, aggregator, mock_get, dd_run_check, omv2_instance):
        """
        Testing CoreDNS check OpenMetrics V2.
        """

        check = CoreDNSCheck(CHECK_NAME, {}, [omv2_instance])
        dd_run_check(check)

        # check that we then get the count metrics also
        dd_run_check(check)

        # `.cache_hits_count.count` metric is only tested against the metrics fixtures file
        # because the metric is not available in docker/e2e.
        metrics = METRICS_V2 + [NAMESPACE + '.cache_hits_count.count']

        for metric in metrics:
            aggregator.assert_metric(metric)
        aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    @pytest.mark.skipif(ON_WINDOWS, reason='No `dig` utility on Windows')
    def test_docker(self, aggregator, dd_environment, dd_run_check, dockerinstance):
        """
        Testing metrics emitted from docker container.
        """

        check = CoreDNSCheck(CHECK_NAME, {}, [dockerinstance])
        dd_run_check(check)

        for metric in METRICS:
            aggregator.assert_metric(metric)

        aggregator.assert_all_metrics_covered()

    @pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
    def test_docker_omv2(self, aggregator, dd_environment, dd_run_check, docker_omv2_instance):
        """
        Testing OpenMetricsV2 metrics emitted from docker container.
        """

        check = CoreDNSCheck(CHECK_NAME, {}, [docker_omv2_instance])
        dd_run_check(check)

        for metric in METRICS_V2:
            aggregator.assert_metric(metric)

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)
