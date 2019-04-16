# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check.check(instance)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)


@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Unix systems")
@pytest.mark.usefixtures("dd_environment")
def test_check_linux(aggregator, check, instance_blacklist):
    check.check(instance_blacklist)

    for metric in common.CONNTRACK_METRICS:
        aggregator.assert_metric(metric)
