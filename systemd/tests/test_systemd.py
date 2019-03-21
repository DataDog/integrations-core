# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.systemd import SystemdCheck

from . import common


def test_check(aggregator, instance_collect_all):
    check = SystemdCheck('systemd', {}, [instance_collect_all])
    check.check(instance_collect_all)
    # expected service check
    status = SystemdCheck.OK
    expected_tags = ['env:test']

    aggregator.assert_service_check(common.EXPECTED_SERVICE_CHECK, status=status,
                                    tags=['unit:ssh.service'] + expected_tags)
    aggregator.assert_service_check(common.EXPECTED_SERVICE_CHECK, status=status,
                                    tags=['unit:networking.service'] + expected_tags)
    aggregator.assert_service_check(common.EXPECTED_SERVICE_CHECK, status=status,
                                    tags=['unit:cron.service'] + expected_tags)

    # expected metrics
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
