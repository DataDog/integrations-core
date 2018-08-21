# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

from datadog_checks.gunicorn import GUnicornCheck

from .common import INSTANCE, CHECK_NAME

log = logging.getLogger('test_gunicorn')


def test_gunicorn(aggregator, setup_gunicorn):
    check = GUnicornCheck(CHECK_NAME, {}, {})
    check.check(INSTANCE)

    aggregator.assert_metric("gunicorn.workers",
                             tags=['app:dd-test-gunicorn', 'state:idle'],
                             value=4,
                             count=1)
    aggregator.assert_metric("gunicorn.workers",
                             tags=['app:dd-test-gunicorn', 'state:working'],
                             value=0,
                             count=1)

    aggregator.assert_service_check("gunicorn.is_running", count=1)

    aggregator.assert_all_metrics_covered()
