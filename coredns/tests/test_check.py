# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.coredns import CoreDNSCheck
from datadog_checks.dev.utils import ON_WINDOWS

CHECK_NAME = 'coredns'
NAMESPACE = 'coredns'


class TestCoreDNS:
    """Basic Test for CoreDNS integration."""

    METRICS = [
        NAMESPACE + '.request_count',
        NAMESPACE + '.cache_size.count',
        NAMESPACE + '.request_type_count',
        NAMESPACE + '.cache_misses_count',
        NAMESPACE + '.response_code_count',
        NAMESPACE + '.proxy_request_count',
        NAMESPACE + '.response_size.bytes.sum',
        NAMESPACE + '.response_size.bytes.count',
        NAMESPACE + '.request_size.bytes.sum',
        NAMESPACE + '.request_size.bytes.count',
        NAMESPACE + '.proxy_request_duration.seconds.sum',
        NAMESPACE + '.proxy_request_duration.seconds.count',
        NAMESPACE + '.request_duration.seconds.sum',
        NAMESPACE + '.request_duration.seconds.count',
        NAMESPACE + '.cache_hits_count',
    ]

    def test_check(self, aggregator, mock_get, instance):
        """
        Testing CoreDNS check.
        """

        check = CoreDNSCheck('coredns', {}, {}, [instance])
        check.check(instance)

        # check that we then get the count metrics also
        check.check(instance)

        for metric in self.METRICS:
            aggregator.assert_metric(metric)

    @pytest.mark.skipif(ON_WINDOWS, reason='No `dig` utility on Windows')
    def test_docker(self, aggregator, dd_environment, dockerinstance):
        """
        Testing metrics emitted from docker container.
        """

        check = CoreDNSCheck('coredns', {}, {}, [dockerinstance])
        check.check(dockerinstance)

        # include_metrics that can be reproduced in a docker based test environment
        include_metrics = [
            NAMESPACE + '.request_count',
            NAMESPACE + '.cache_size.count',
            NAMESPACE + '.request_type_count',
            NAMESPACE + '.cache_misses_count',
            NAMESPACE + '.response_code_count',
            NAMESPACE + '.proxy_request_count',
            NAMESPACE + '.response_size.bytes.sum',
            NAMESPACE + '.response_size.bytes.count',
            NAMESPACE + '.request_size.bytes.sum',
            NAMESPACE + '.request_size.bytes.count',
            NAMESPACE + '.proxy_request_duration.seconds.sum',
            NAMESPACE + '.proxy_request_duration.seconds.count',
            NAMESPACE + '.request_duration.seconds.sum',
            NAMESPACE + '.request_duration.seconds.count',
        ]

        for metric in include_metrics:
            aggregator.assert_metric(metric)
