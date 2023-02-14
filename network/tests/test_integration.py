# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import platform

import pytest

from datadog_checks.base.utils.platform import Platform
from datadog_checks.dev.utils import get_metadata_metrics

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check_instance = check(instance)
    check_instance.check({})

    expected_metrics = copy.deepcopy(common.EXPECTED_METRICS)
    if Platform.is_windows() or Platform.is_linux():
        expected_metrics += common.EXPECTED_WINDOWS_LINUX_METRICS
    for metric in expected_metrics:
        aggregator.assert_metric(metric)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Linux systems")
@pytest.mark.usefixtures("dd_environment")
def test_check_linux(aggregator, check, instance_blacklist):
    check_instance = check(instance_blacklist)
    check_instance.check({})

    for metric in common.CONNTRACK_METRICS:
        aggregator.assert_metric(metric)
