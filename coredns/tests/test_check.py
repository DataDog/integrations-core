# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.coredns import CoreDNSCheck
from datadog_checks.dev.utils import ON_WINDOWS

from .common import CHECK_NAME, METRICS, NAMESPACE


class TestCoreDNS:
    """Basic Test for CoreDNS integration."""

    def test_check(self, aggregator, mock_get, instance):
        """
        Testing CoreDNS check.
        """

        check = CoreDNSCheck(CHECK_NAME, {}, [instance])
        check.check(instance)

        # check that we then get the count metrics also
        check.check(instance)

        metrics = METRICS + [NAMESPACE + '.cache_hits_count']

        for metric in metrics:
            aggregator.assert_metric(metric)

    @pytest.mark.skipif(ON_WINDOWS, reason='No `dig` utility on Windows')
    def test_docker(self, aggregator, dd_environment, dockerinstance):
        """
        Testing metrics emitted from docker container.
        """

        check = CoreDNSCheck(CHECK_NAME, {}, [dockerinstance])
        check.check(dockerinstance)

        for metric in METRICS:
            aggregator.assert_metric(metric)
