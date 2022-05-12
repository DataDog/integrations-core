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
