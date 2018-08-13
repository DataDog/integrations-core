# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.gunicorn import GUnicornCheck

from .common import INSTANCE, CHECK_NAME


def test_gunicorn(aggregator, setup_gunicorn):
    check = GUnicornCheck(CHECK_NAME, {}, {})
    check.check(INSTANCE)

    aggregator.assert_metric("gunicorn.workers",
                             tags=['app:dd-test-gunicorn', 'state:idle', 'optional:tag1'],
                             at_least=0)
    aggregator.assert_metric("gunicorn.workers",
                             tags=['app:dd-test-gunicorn', 'state:working', 'optional:tag1'],
                             at_least=0)

    aggregator.assert_service_check("gunicorn.is_running", count=1)

    aggregator.assert_all_metrics_covered()
