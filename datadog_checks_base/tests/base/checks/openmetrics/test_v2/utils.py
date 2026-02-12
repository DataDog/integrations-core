# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

# Patch target for mock_http_response: scraper calls self.http.get(endpoint, ...).
OPENMETRICS_SCRAPER_HTTP_TARGET = (
    'datadog_checks.base.checks.openmetrics.v2.scraper.base_scraper.RequestsWrapper.get'
)


def get_check(instance=None, init_config=None):
    return _get_check(OpenMetricsBaseCheckV2, instance, init_config)


def _get_check(cls, instance, init_config):
    if instance is None:
        instance = {}
    if init_config is None:
        init_config = {}

    instance.setdefault('openmetrics_endpoint', 'test')
    check = cls('test', init_config, [instance])
    check.__NAMESPACE__ = 'test'

    return check
