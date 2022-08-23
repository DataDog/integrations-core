# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.tdd import TddCheck

from .common import HOST, PORT, standalone


@standalone
@pytest.mark.e2e
def test_e2e_mongo_standalone(dd_agent_check):
    instance = {'hosts': ['{}:{}'.format(HOST, PORT)], 'username': 'testUser', 'password': 'testPass'}
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check('tdd.can_connect', status=TddCheck.OK)
