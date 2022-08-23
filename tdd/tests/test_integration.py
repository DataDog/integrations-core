# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tdd import TddCheck

from .common import HOST, PORT_ERROR, standalone


@standalone
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_integration_mongo_standalone_critical(dd_run_check, aggregator):
    instance = {'hosts': ['{}:{}'.format(HOST, PORT_ERROR)], 'username': 'testUser', 'password': 'testPass'}
    check = TddCheck('tdd', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('tdd.can_connect', TddCheck.CRITICAL)
