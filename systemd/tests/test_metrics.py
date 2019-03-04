# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.systemd import SystemdCheck
from datadog_checks.systemd.systemd import (
    get_all_units, get_active_inactive_units, get_number_processes
)


@pytest.mark.unit
def test_cache(instance):
    # check that we're getting a cache with unit_ids and unit_state
    check = SystemdCheck('systemd', {}, [instance])
    check.unit_cache
    cache_test = get_all_units()
    assert len(check.unit_cache) > 1
    assert cache_test == {"units": {"networking.service": "active", "cron.service": "active", "ssh.service": "active"}}


@pytest.mark.unit
def test_collect_all():
    # check that we are getting both inactive and active units
    all_unit_state = get_active_inactive_units()
    aggregator.assert_metric('systemd.units.active')
    aggregator.assert_metric('systemd.units.inactive')


@pytest.mark.unit
def test_get_number_processes():
    # check we are getting at least one process for a given unit that is active
    number_processes = get_number_processes('httpd.service')
    assert number_processes >= 1
