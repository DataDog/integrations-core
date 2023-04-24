# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.strimzi import StrimziCheck

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(dd_run_check, aggregator, check, instance):
    dd_run_check(check(instance))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, check, instance):
    dd_run_check(check(instance))
    aggregator.assert_service_check('strimzi.can_connect', StrimziCheck.CRITICAL)
