# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tcp_check import TCPCheck

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check.check(instance)
    common._test_check(aggregator, check._addrs)
    assert len(check._addrs) == 1


@pytest.mark.usefixtures("dd_environment")
def test_check_multiple(aggregator):
    check = TCPCheck(common.CHECK_NAME, {}, [common.INSTANCE_MULTIPLE])
    check.check(None)
    common._test_check(aggregator, check._addrs)
    assert len(check._addrs) == 4
