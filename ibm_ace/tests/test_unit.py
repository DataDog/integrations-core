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
