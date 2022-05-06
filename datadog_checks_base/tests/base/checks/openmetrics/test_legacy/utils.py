# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

# TODO: remove `try` when we drop Python 2
try:
    from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

    class LegacyCheck(OpenMetricsBaseCheckV2):
        def create_scraper(self, config):
            return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

except Exception:
    pass


def get_legacy_check(instance=None, init_config=None):
    return _get_check(LegacyCheck, instance, init_config)


def _get_check(cls, instance, init_config):
    if instance is None:
        instance = {}
    if init_config is None:
        init_config = {}

    instance.setdefault('openmetrics_endpoint', 'test')
    check = cls('test', init_config, [instance])
    check.__NAMESPACE__ = 'test'

    return check
