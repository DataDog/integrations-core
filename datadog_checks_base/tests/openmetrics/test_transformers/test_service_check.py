# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from ...utils import requires_py3
from ..utils import get_check

pytestmark = [
    requires_py3,
    pytest.mark.openmetrics,
    pytest.mark.openmetrics_transformers,
    pytest.mark.openmetrics_transformers_service_check,
]


def test_known(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP state Node state
        # TYPE state gauge
        state{foo="bar"} 3
        """
    )
    check = get_check({'metrics': [{'state': {'type': 'service_check', 'status_map': {'3': 'ok'}}}]})
    dd_run_check(check)

    aggregator.assert_service_check('test.state', ServiceCheck.OK, tags=['endpoint:test'])

    aggregator.assert_all_metrics_covered()


def test_unknown(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP state Node state
        # TYPE state gauge
        state{foo="bar"} 3
        """
    )
    check = get_check({'metrics': [{'state': {'type': 'service_check', 'status_map': {'7': 'ok'}}}]})
    dd_run_check(check)

    aggregator.assert_service_check('test.state', ServiceCheck.UNKNOWN, tags=['endpoint:test'])

    aggregator.assert_all_metrics_covered()
