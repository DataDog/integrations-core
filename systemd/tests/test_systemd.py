# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.systemd import SystemdCheck


def test_check(aggregator, instance):
    check = SystemdCheck('systemd', {}, [instance])
    check.check(instance)
    # expected service checks
    aggregator.assert_service_check('systemd.unit.active', status=SystemdCheck.OK)
    # expected metric
    aggregator.assert_metric('systemd.unit.processes')
