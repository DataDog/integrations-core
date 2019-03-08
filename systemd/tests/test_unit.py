# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.systemd import SystemdCheck
from .mocks import mock_systemd_output


def test_config_options(instance):
    check = SystemdCheck('systemd', {}, [instance])

    assert check.collect_all is False
    assert len(check.units) == 3


def test_bad_config(instance):
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        SystemdCheck('systemd', {}, [instance, instance])


def test_unit_not_found(aggregator, instance_ko):
    check = SystemdCheck('systemd', {}, [instance_ko])
    check.check(instance_ko)

    aggregator.assert_service_check('systemd.unit.active')


def test_collect_all_units(aggregator, instance_collect_all):
    check = SystemdCheck('systemd', {}, [instance_collect_all])
    check.check(instance_collect_all)

    aggregator.assert_metric('systemd.units.active')
    aggregator.assert_metric('systemd.units.inactive')


"""
@pytest.mark.usefixtures('systemd_mocks')
def test_systemd(aggregator, gauge_metrics, instance):
    instance = instance
    check = SystemdCheck('systemd', {}, [instance])

    mock_output = mock.patch(
        'datadog_checks.systemd.systemd.get_subprocess_output',
        return_value=mock_systemd_output('debian-systemctl'),
        __name__='get_systemd_output'
    )

    with mock_output:
        check.check(instance)

    for name in iteritems(gauge_metrics):
        aggregator.assert_metric(name, value=value)
"""


@pytest.mark.unit
def test_cache(instance):
    # the cache should be empty at the beginning
    check = SystemdCheck('systemd', {}, [instance])
    assert len(check.unit_cache) == 0
    # assert cache_test == {"units": {"networking.service": "active", "cron.service": "active",
    # "ssh.service": "active"}}
