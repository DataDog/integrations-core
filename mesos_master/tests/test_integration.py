# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.mesos_master import MesosMaster

from .common import not_windows_ci

pytestmark = not_windows_ci


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_service_check(bad_instance, aggregator):
    check = MesosMaster('mesos_master', {}, [bad_instance])

    with pytest.raises(CheckException):
        check.check(bad_instance)

    aggregator.assert_service_check('mesos_master.can_connect', count=1, status=AgentCheck.CRITICAL)
