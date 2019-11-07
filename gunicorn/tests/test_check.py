# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.gunicorn import GUnicornCheck

from .common import CHECK_NAME, INSTANCE


def _assert_metrics(aggregator):
    aggregator.assert_metric("gunicorn.workers", tags=['app:dd-test-gunicorn', 'state:idle'], value=4, count=1)
    aggregator.assert_metric("gunicorn.workers", tags=['app:dd-test-gunicorn', 'state:working'], value=0, count=1)

    aggregator.assert_service_check("gunicorn.is_running", count=1)

    aggregator.assert_all_metrics_covered()


def test_gunicorn_instance(aggregator, setup_gunicorn):
    instance = INSTANCE.copy()
    instance['gunicorn'] = setup_gunicorn['gunicorn_bin_path']

    check = GUnicornCheck(CHECK_NAME, {}, [instance])
    check.check(instance)
    _assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE)
    _assert_metrics(aggregator)
