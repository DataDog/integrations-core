# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ..utils import get_check


def test(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP istio_requests_total requests_total
        # TYPE istio_requests_total counter
        istio_requests_total 6.396288e+06
        """
    )
    check = get_check({'metrics': [{'istio_requests': {'type': 'rate'}}]})
    dd_run_check(check)

    aggregator.assert_metric('test.istio_requests', 6396288, metric_type=aggregator.RATE, tags=['endpoint:test'])

    aggregator.assert_all_metrics_covered()
