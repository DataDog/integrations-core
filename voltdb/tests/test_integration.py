# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import hashlib

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.voltdb import VoltDBCheck
from datadog_checks.voltdb.types import Instance

from . import assertions, common


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestCheck:
    def test_check(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        check = VoltDBCheck('voltdb', {}, [instance])
        check.run()
        assertions.assert_service_checks(aggregator, instance)
        assertions.assert_metrics(aggregator)

    def test_password_hashed(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['password'] = hashlib.sha256(instance['password'].encode()).hexdigest()
        instance['password_hashed'] = True

        check = VoltDBCheck('voltdb', {}, [instance])
        check.run()

        assertions.assert_service_checks(aggregator, instance)
        assertions.assert_metrics(aggregator)

    def test_failure_connection_refused(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['url'] = instance['url'].replace(common.HOST, 'doesnotexist')

        check = VoltDBCheck('voltdb', {}, [instance])

        with pytest.raises(Exception) as ctx:
            check.check(instance)
        error = str(ctx.value)
        assert 'nodename nor servname provided' in error

        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL)

    def test_failure_unauthorized(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance.pop('username')
        instance.pop('password')

        check = VoltDBCheck('voltdb', {}, [instance])

        with pytest.raises(Exception) as ctx:
            check.check(instance)
        error = str(ctx.value)
        assert '401 Client Error: Unauthorized' in error

        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL)
