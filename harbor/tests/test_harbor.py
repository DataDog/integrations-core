# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.harbor import HarborCheck
from .common import HARBOR_STATUS_CHECKS, HARBOR_METRICS


HARBOR_VERSION = list(map(lambda x: int(x), os.getenv("HARBOR_VERSION").split('.')))


@pytest.mark.integration
def test_check(aggregator, instance):
    check = HarborCheck('harbor', {}, [instance])
    check.check(instance)
    for status_check, min_version in HARBOR_STATUS_CHECKS:
        if not min_version or HARBOR_VERSION >= min_version:
            aggregator.assert_service_check(status_check)
    for metric in HARBOR_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
