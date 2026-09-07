# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.ibm_ace.check import IbmAceCheck
from datadog_checks.ibm_ace.resources import get_resource
from datadog_checks.ibm_ace.subscription import FlowMonitoringSubscription, ResourceStatisticsSubscription

from .common import HERE


def test_flow_monitoring_subscription(instance, global_tags):
    check = IbmAceCheck('ibm_ace', {}, [instance])
    flow_monitoring_subscription = FlowMonitoringSubscription(check, global_tags)
    mock_payload = b'{"object": "value"}'
    mock_message = {
        'WMQIStatisticsAccounting': {
            'RecordType': 'SnapShot',
            'RecordCode': 'SnapShot',
            'MessageFlow': {
                'BrokerLabel': 'integration_server',
                'BrokerUUID': '',
                'ExecutionGroupName': 'ACESERVER',
                'MessageFlowName': 'Caller',
                'ApplicationName': 'CallHTTPSEcho',
            },
        }
    }
    assert flow_monitoring_subscription.parse_message(mock_payload) == {'object': 'value'}
    assert flow_monitoring_subscription.get_message_id(mock_message) == ('integration_server', 'ACESERVER', 'Caller')


def test_resource_statistics_subscription(instance, global_tags):
    check = IbmAceCheck('ibm_ace', {}, [instance])
    resource_statistics_subscription = ResourceStatisticsSubscription(check, global_tags)
    mock_message = {
        'ResourceStatistics': {
            'brokerLabel': 'integration_server',
            'brokerUUID': '',
            'executionGroupName': 'ACESERVER',
            'executionGroupUUID': '00000000-0000-0000-0000-000000000000',
        }
    }

    assert resource_statistics_subscription.get_message_id(mock_message) == ('integration_server', 'ACESERVER')


def test_truncated_message_given_oversized_payload_skips_without_critical(instance, global_tags):
    from unittest.mock import MagicMock, PropertyMock, patch

    import pymqi

    from datadog_checks.base.constants import ServiceCheck

    mock_config = MagicMock()
    mock_config.max_message_length = 65536

    check = IbmAceCheck('ibm_ace', {}, [instance])
    check.log = MagicMock()
    check.service_check = MagicMock()
    check.gauge = MagicMock()

    sub = ResourceStatisticsSubscription(check, global_tags)

    truncation_error = pymqi.MQMIError(pymqi.CMQC.MQCC_FAILED, pymqi.CMQC.MQRC_TRUNCATED_MSG_FAILED)

    mock_sub = MagicMock()
    mock_sub.get.side_effect = truncation_error

    with (
        patch.object(type(check), 'config', new_callable=PropertyMock, return_value=mock_config),
        patch.object(type(sub), 'sub', new_callable=PropertyMock, return_value=mock_sub),
    ):
        messages = sub.get_latest_messages()

    assert messages == []
    check.log.warning.assert_any_call(
        'Message on subscription %s exceeded %d-byte buffer and was skipped. '
        'Increase max_message_length in the integration configuration.',
        'resource_statistics',
        65536,
    )
    check.log.error.assert_not_called()

    sc_calls = [c for c in check.service_check.call_args_list if c[0][0] == 'mq.subscription']
    assert len(sc_calls) == 1
    assert sc_calls[0][0][1] == ServiceCheck.WARNING


def test_non_truncation_error_given_connection_broken_returns_critical(instance, global_tags):
    from unittest.mock import MagicMock, PropertyMock, patch

    import pymqi

    from datadog_checks.base.constants import ServiceCheck

    mock_config = MagicMock()
    mock_config.max_message_length = 65536

    check = IbmAceCheck('ibm_ace', {}, [instance])
    check.log = MagicMock()
    check.service_check = MagicMock()
    check.gauge = MagicMock()

    sub = ResourceStatisticsSubscription(check, global_tags)

    connection_error = pymqi.MQMIError(pymqi.CMQC.MQCC_FAILED, pymqi.CMQC.MQRC_CONNECTION_BROKEN)

    mock_sub = MagicMock()
    mock_sub.get.side_effect = connection_error

    with (
        patch.object(type(check), 'config', new_callable=PropertyMock, return_value=mock_config),
        patch.object(type(sub), 'sub', new_callable=PropertyMock, return_value=mock_sub),
        patch.object(sub, '_get_elapsed_time', return_value=25),
    ):
        messages = sub.get_latest_messages()

    assert messages == []
    check.log.error.assert_called_once()

    sc_calls = [c for c in check.service_check.call_args_list if c[0][0] == 'mq.subscription']
    assert len(sc_calls) == 1
    assert sc_calls[0][0][1] == ServiceCheck.CRITICAL


def test_parse_tags_with_name():
    resource = get_resource('JDBCConnectionPools')
    metric_data = {'name': 'MyDataSource', 'NameOfJDBCProvider': 'Oracle'}

    tags = resource.parse_tags(['mq_server:x'], metric_data)

    assert tags == ['group:MyDataSource', 'mq_server:x', 'jdbc_provider:Oracle']


def test_parse_tags_without_name():
    # ACE can omit `name`; this must not raise.
    resource = get_resource('JDBCConnectionPools')
    metric_data = {'NameOfJDBCProvider': 'Oracle'}

    tags = resource.parse_tags(['mq_server:x'], metric_data)

    assert tags == ['mq_server:x', 'jdbc_provider:Oracle']


def test_collect_survives_malformed_resource_identifier(instance, global_tags, caplog):
    # ACE 12.0.9 payload where repeated `resourceIdentifier` entries
    # have their `name` key replaced with an empty string. Must not crash.
    import logging
    from unittest.mock import MagicMock, PropertyMock, patch

    caplog.set_level(logging.DEBUG)

    fixture_path = os.path.join(HERE, 'fixtures', 'resource_statistics_malformed_jdbc.json')
    with open(fixture_path, 'rb') as f:
        payload = f.read()

    mock_config = MagicMock()
    mock_config.max_message_length = 65536

    check = IbmAceCheck('ibm_ace', {}, [instance])
    check.gauge = MagicMock()
    check.count = MagicMock()
    check.service_check = MagicMock()

    sub = ResourceStatisticsSubscription(check, global_tags)

    mock_sub = MagicMock()
    mock_sub.get.side_effect = [payload]

    with (
        patch.object(type(check), 'config', new_callable=PropertyMock, return_value=mock_config),
        patch.object(type(sub), 'sub', new_callable=PropertyMock, return_value=mock_sub),
        patch.object(sub, '_get_elapsed_time', return_value=25),
    ):
        sub.collect()  # must not raise

    submitted = check.count.call_args_list + check.gauge.call_args_list
    submitted_metrics = {c.args[0] for c in submitted}

    # `self.check.count`/`.gauge` are mocked directly, so the `ibm_ace.` namespace
    # prefix (normally applied inside AgentCheck.count/gauge) isn't present here.
    assert 'JDBCConnectionPools.CumulativeRequests' in submitted_metrics
    # The malformed entries' empty-string key must never become a metric name.
    assert not any(c.args[0].endswith('.') for c in submitted)

    # The well-formed entry still gets its `group` tag; the malformed ones don't.
    well_formed_call = next(
        c for c in submitted if 'jdbc_provider:jdbc_DataSourceA' in c.kwargs['tags'] and c.args[1] == 891
    )
    assert any(tag.startswith('group:') for tag in well_formed_call.kwargs['tags'])

    malformed_calls = [c for c in submitted if 'jdbc_provider:jdbc_DataSourceB' in c.kwargs['tags']]
    assert malformed_calls
    assert not any(tag.startswith('group:') for c in malformed_calls for tag in c.kwargs['tags'])

    # The fixture has two malformed entries; each is logged at debug level when skipped.
    skip_lines = [r for r in caplog.records if 'Skipping resourceIdentifier entry with malformed key' in r.message]
    assert len(skip_lines) == 2
    for record in skip_lines:
        assert record.levelname == 'DEBUG'
        assert 'JDBCConnectionPools' in record.message
        assert "value='summary0'" in record.message
