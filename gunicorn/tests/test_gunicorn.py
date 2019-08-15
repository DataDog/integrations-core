# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

import pytest

from datadog_checks.gunicorn import GUnicornCheck

from .common import CHECK_NAME, INSTANCE

log = logging.getLogger('test_gunicorn')


def _assert_metrics(aggregator):
    aggregator.assert_metric("gunicorn.workers", tags=['app:dd-test-gunicorn', 'state:idle'], value=4, count=1)
    aggregator.assert_metric("gunicorn.workers", tags=['app:dd-test-gunicorn', 'state:working'], value=0, count=1)

    aggregator.assert_service_check("gunicorn.is_running", count=1)

    aggregator.assert_all_metrics_covered()


def test_gunicorn(aggregator, setup_gunicorn):
    check = GUnicornCheck(CHECK_NAME, {}, {})
    check.check(INSTANCE)
    _assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE)
    _assert_metrics(aggregator)
