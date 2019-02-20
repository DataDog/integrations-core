# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.systemd.systemd import (
    get_all_units, get_active_inactive_units
)

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.mark.unit
def test_cache():
    # check that we're getting a cache with unit_ids and unit_state
    cache_test = get_all_units()
    assert len(cache_test) > 1
    assert cache_test == {"units": {"networking.service": "active", "cron.service": "active", "ssh.service": "active"}}


@pytest.mark.unit
def test_collect_all(aggregator, check, instance):
    # check that we are getting both inactive and active units
    all_unit_state = get_active_inactive_units()
    aggregator.assert_metric('systemd.units.active')
    aggregator.assert_metric('systemd.units.inactive')
