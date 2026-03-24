# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ibm_ace.check import IbmAceCheck
from datadog_checks.ibm_ace.subscription import FlowMonitoringSubscription, ResourceStatisticsSubscription


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

    from datadog_checks.ibm_ace.subscription import SNAPSHOT_UPDATE_INTERVAL

    check = IbmAceCheck('ibm_ace', {}, [instance])
    check.config = MagicMock()
    check.config.max_message_length = 65536
    check.log = MagicMock()

    sub = ResourceStatisticsSubscription(check, global_tags)

    truncation_error = pymqi.MQMIError(pymqi.CMQC.MQCC_FAILED, pymqi.CMQC.MQRC_TRUNCATED_MSG_FAILED)

    mock_sub = MagicMock()
    mock_sub.get.side_effect = truncation_error

    with (
        patch.object(type(sub), 'sub', new_callable=PropertyMock, return_value=mock_sub),
    ):
        messages = sub.get_latest_messages()

    assert messages == []
    check.log.warning.assert_called_once()
