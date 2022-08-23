# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tdd import TddCheck


def test_check(dd_run_check, aggregator, instance):
    check = TddCheck('tdd', {}, [instance])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
    check = TddCheck('tdd', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('tdd.can_connect', TddCheck.CRITICAL)
