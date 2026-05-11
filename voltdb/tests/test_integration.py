# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable  # noqa: F401

import mock
import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub  # noqa: F401
from datadog_checks.voltdb import VoltDBCheck
from datadog_checks.voltdb.client import Client
from datadog_checks.voltdb.types import Instance  # noqa: F401

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

    def test_failure_connection_refused(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['host'] = 'doesnotexist'
        # Speed up the test
        instance['connect_timeout'] = 2

        check = VoltDBCheck('voltdb', {}, [instance])

        with pytest.raises(Exception):
            check.check(instance)

        tags = ['host:doesnotexist', 'port:{}'.format(instance.get('port', 21212))]
        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL, tags=tags)

    def test_failure_unauthorized(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['password'] = 'wrongpass'

        check = VoltDBCheck('voltdb', {}, [instance])

        with pytest.raises(Exception):
            check.check(instance)

        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL)

    def test_custom_tags(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['tags'] = ['env:test']

        check = VoltDBCheck('voltdb', {}, [instance])
        check.run()

        metrics_without_custom_tags = []
        for metric_names, _ in common.METRICS:
            for metric_name in metric_names:
                for metric in aggregator.metrics(metric_name):
                    if 'env:test' not in metric.tags:
                        metrics_without_custom_tags.append(metric_name)

        assert not metrics_without_custom_tags


class MockSysInfoClient(Client):
    def __init__(self, client, app):
        # type: (Client, Callable) -> None
        self._client = client
        self._app = app

    def call_procedure(self, procedure, params=None):
        if procedure == '@SystemInformation':
            return self._app()
        return self._client.call_procedure(procedure, params=params)

    def raise_for_status(self, response):
        # Mock responses already have status set by the test app.
        if response.status != Client.SUCCESS:
            self._client.raise_for_status(response)

    def close(self):
        self._client.close()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestVersionMetadata:
    @pytest.mark.integration
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

        check_id = 'test'
        check = VoltDBCheck('voltdb', {}, [instance])
        check.check_id = check_id
        error = check.run()
        assert not error
        datadog_agent.assert_metadata(check_id, metadata)

    @pytest.mark.integration
    def test_malformed(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        def app():
            table = mock.MagicMock()
            table.tuples = [('0', 'VERSION', 'not_a_version_string')]
            table.columns = [
                mock.MagicMock(**{'name': 'HOST_ID'}),
                mock.MagicMock(**{'name': 'KEY'}),
                mock.MagicMock(**{'name': 'VALUE'}),
            ]
            resp = mock.MagicMock()
            resp.status = Client.SUCCESS
            resp.tables = [table]
            return resp

        check_id = 'test'
        check = VoltDBCheck('voltdb', {}, [instance])
        check.check_id = check_id
        check._client = MockSysInfoClient(check._client, app)
        error = check.run()
        assert not error
        datadog_agent.assert_metadata(check_id, {})

    @pytest.mark.integration
    def test_failure(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        def app():
            raise ValueError('Oops!')

        check_id = 'test'
        check = VoltDBCheck('voltdb', {}, [instance])
        check.check_id = check_id
        check._client = MockSysInfoClient(check._client, app)
        error = check.run()
        assert 'Oops!' in error
        datadog_agent.assert_metadata(check_id, {})

    @pytest.mark.integration
    def test_no_version_column(self, aggregator, instance, datadog_agent):
        # type: (AggregatorStub, Instance, DatadogAgentStub) -> None
        def app():
            table = mock.MagicMock()
            table.tuples = [('0', 'THIS_IS_NOT_VERSION', 'test')]
            table.columns = [
                mock.MagicMock(**{'name': 'HOST_ID'}),
                mock.MagicMock(**{'name': 'KEY'}),
                mock.MagicMock(**{'name': 'VALUE'}),
            ]
            resp = mock.MagicMock()
            resp.status = Client.SUCCESS
            resp.tables = [table]
            return resp

        check_id = 'test'
        check = VoltDBCheck('voltdb', {}, [instance])
        check.check_id = check_id
        check._client = MockSysInfoClient(check._client, app)
        error = check.run()
        assert not error
        datadog_agent.assert_metadata(check_id, {})
