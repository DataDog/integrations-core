# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.systemd import SystemdCheck


def test_config_options(instance):
    check = SystemdCheck('systemd', {}, [instance])

    assert check.report_status is False
    assert check.report_processes is True
    assert len(check.units_watched) == 3


def test_bad_config(instance):
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        SystemdCheck('systemd', {}, [instance, instance])


def test_cache(instance):
    check = SystemdCheck('systemd', {}, [instance])
    # check that the cache is empty when at the beginning
    assert len(check.unit_cache) == 0
    current_unit_status = {'ssh.service': 'active', 'cron.service': 'active', 'networking.service': 'inactive'}
    assert check.list_status_change(current_unit_status) is not None
    assert len(check.list_status_change(current_unit_status)) == 3
