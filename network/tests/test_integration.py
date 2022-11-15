# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest

from datadog_checks.network.check_bsd import BSDNetwork
from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check_instance = check(instance)
    check_instance.check({})

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)


@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Linux systems")
@pytest.mark.usefixtures("dd_environment")
def test_check_linux(aggregator, check, instance_blacklist):
    check_instance = check(instance_blacklist)
    check_instance.check({})

    for metric in common.CONNTRACK_METRICS:
        aggregator.assert_metric(metric)


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@pytest.mark.usefixtures("dd_environment")
def test_check_bsd(instance, aggregator):
    check = BSDNetwork('network', {}, [instance])
    check.check({})
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
