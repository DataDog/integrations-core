# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import hashlib

import mock
import pytest
import requests

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
        instance['url'] = 'http://doesnotexist:8080'

        check = VoltDBCheck('voltdb', {}, [instance])

        with pytest.raises(Exception) as ctx:
            check.check(instance)
        error = str(ctx.value)
        assert error

        tags = ['host:doesnotexist', 'port:8080']
        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL, tags=tags)

    def test_failure_unauthorized(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        instance = instance.copy()
        instance['password'] = 'wrongpass'

        check = VoltDBCheck('voltdb', {}, [instance])

        with pytest.raises(Exception) as ctx:
            check.check(instance)
        error = str(ctx.value)
        assert '401 Client Error: Unauthorized' in error

        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL)

    def test_http_error(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        check = VoltDBCheck('voltdb', {}, [instance])

        with mock.patch('requests.get', side_effect=requests.RequestException('Something failed')):
            error = check.run()

        assert 'Something failed' in error

        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL)
        aggregator.assert_all_metrics_covered()  # No metrics collected.

    def test_http_response_error(self, aggregator, instance):
        # type: (AggregatorStub, Instance) -> None
        check = VoltDBCheck('voltdb', {}, [instance])

        resp = requests.Response()
        resp.status_code = 503
        with mock.patch('requests.get', return_value=resp):
            error = check.run()

        assert '503 Server Error' in error

        assertions.assert_service_checks(aggregator, instance, connect_status=VoltDBCheck.CRITICAL)
        aggregator.assert_all_metrics_covered()  # No metrics collected.

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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
class TestVersionMetadata:
    VERSION_MOCK_TARGET = 'datadog_checks.voltdb.VoltDBCheck._fetch_version'
    SYSTEM_INFORMATION_MOCK = 'datadog_checks.voltdb.VoltDBCheck._get_system_information'

    def _run_test(self, instance, datadog_agent, metadata, error_contains=''):
        # type: (Instance, DatadogAgentStub, dict, str) -> None
        check_id = 'test'
        check = VoltDBCheck('voltdb', {}, [instance])
        check.check_id = check_id
        error = check.run()
        if error_contains:
            assert error_contains in error
        datadog_agent.assert_metadata(check_id, metadata)

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

        self._run_test(instance, datadog_agent, metadata=metadata)

    @pytest.mark.integration
    def test_malformed(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        malformed_version_string = 'obviously_not_a_version_string'
        with mock.patch(self.VERSION_MOCK_TARGET, return_value=malformed_version_string):
            self._run_test(instance, datadog_agent, metadata={})

    @pytest.mark.integration
    def test_failure(self, instance, datadog_agent):
        # type: (Instance, DatadogAgentStub) -> None
        with mock.patch(self.VERSION_MOCK_TARGET, side_effect=ValueError('Oops!')):
            self._run_test(instance, datadog_agent, metadata={}, error_contains='Oops!')

    @pytest.mark.integration
    def test_no_version_column(self, aggregator, instance, datadog_agent):
        # type: (AggregatorStub, Instance, DatadogAgentStub) -> None
        with mock.patch(self.SYSTEM_INFORMATION_MOCK) as m:
            row = ('0', 'THIS_IS_NOT_VERSION', 'test')
            r = mock.MagicMock()
            r.json.return_value = {'results': [{'data': [row]}]}  # Respect response payload format.
            m.return_value = r
            self._run_test(instance, datadog_agent, metadata={})
