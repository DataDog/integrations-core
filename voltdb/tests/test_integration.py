# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import hashlib

import mock
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub
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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestVersionMetadata:
    VERSION_MOCK_TARGET = 'datadog_checks.voltdb.VoltDBCheck._fetch_version'

    def _run_test(self, instance, datadog_agent, metadata):
        # type: (Instance, DatadogAgentStub, dict) -> None
        check_id = 'test'
        check = VoltDBCheck('voltdb', {}, [instance])
        check.check_id = check_id
        error = check.run()
        assert not error
        datadog_agent.assert_metadata(check_id, metadata)

    def test_default(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        version = common.VOLTDB_VERSION
        major, minor, patch = version.split('.')
        metadata = {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': version,
        }

        self._run_test(instance, datadog_agent, metadata=metadata)

    @pytest.mark.integration
    def test_malformed(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        malformed_version_string = 'obviously_not_a_version_string'
        with mock.patch(self.VERSION_MOCK_TARGET, return_value=malformed_version_string):
            # Should not fail.
            self._run_test(instance, datadog_agent, metadata={})

    @pytest.mark.integration
    def test_failure(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        with mock.patch(self.VERSION_MOCK_TARGET, side_effect=ValueError('Oops!')):
            # Should not fail.
            self._run_test(instance, datadog_agent, metadata={})
