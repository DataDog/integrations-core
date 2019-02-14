# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import subprocess

from datadog_checks.systemd import SystemdCheck
from datadog_checks.errors import CheckException

from datadog_checks.utils.common import get_docker_hostname


def test_check(aggregator, check):
    check.check(instance)

    aggregator.assert_all_metrics_covered()


def test_units_active(aggregator, check, instance):
    """
    Those above units are expected to be active
    """
    check.check(instance)
    aggregator.assert_service_check('systemd.unit.active', SystemdCheck.OK)

def test_units_not_found(aggregator, check, instance_ko):
    with pytest.raises(pystemd.dbusexc.DBusInvalidArgsError):
        check.check(instance_ko)
