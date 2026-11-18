# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.common import HostingType, StandaloneDeployment
from datadog_checks.mongo.dbm.utils import get_operation_comment


@pytest.mark.unit
@pytest.mark.parametrize('application', ['datadog-agent', 'orders', 'agent', None])
@pytest.mark.parametrize('comment', [None, "ddps='orders'", {'query_source': 'agent-count'}, ['one', 'two']])
def test_operation_comment_preserves_customer_identity(application: str | None, comment: object):
    command = {'find': 'orders'}
    if comment is not None:
        command['comment'] = comment
    result = get_operation_comment(command, application)
    assert result == ("service='datadog-agent'" if application == 'datadog-agent' else comment)
    assert command.get('comment') == comment


@pytest.mark.unit
@pytest.mark.parametrize('application', ['datadog-agent', 'orders', None])
def test_agent_service_on_activity_and_plan_metadata(application: str | None):
    check = MongoDb('mongo', {}, [{'hosts': ['localhost:27017'], 'dbm': True, 'cluster_name': 'test-cluster'}])
    check.deployment_type = StandaloneDeployment(HostingType.SELF_HOSTED)
    operation = {'ns': 'test.orders', 'command': {'find': 'orders'}, 'appName': application}
    metadata = check._operation_samples._get_operation_metadata(operation)
    expected = "service='datadog-agent'" if application == 'datadog-agent' else None
    assert metadata['comment'] == expected
    activity = check._operation_samples._create_activity(1, operation, metadata, '{}', 'signature')
    assert activity['comment'] == expected
    sample = check._operation_samples._create_operation_sample_payload(1, metadata, '{}', 'signature', {}, activity)
    assert sample['db']['operation_metadata']['comment'] == expected
    check.cancel()


@pytest.mark.unit
@pytest.mark.parametrize('application', ['datadog-agent', 'orders', None])
def test_agent_service_on_slow_operation(application: str | None):
    check = MongoDb('mongo', {}, [{'hosts': ['localhost:27017'], 'dbm': True, 'cluster_name': 'test-cluster'}])
    operation = {
        'ts': 1,
        'dbname': 'test',
        'query_signature': 'signature',
        'obfuscated_command': '{}',
        'command': {'find': 'orders'},
        'appName': application,
    }
    event = check._slow_operations._create_slow_operation_event(operation)
    assert event.get('comment') == ("service='datadog-agent'" if application == 'datadog-agent' else None)
    check.cancel()
