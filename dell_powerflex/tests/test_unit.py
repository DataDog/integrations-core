# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

from requests.exceptions import ConnectionError

from datadog_checks.dell_powerflex import DellPowerflexCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import SYSTEM_MDM_CLUSTER_METRICS, SYSTEM_STATS_BWC_METRICS, SYSTEM_STATS_SIMPLE_METRICS


def test_can_connect_down(dd_run_check, aggregator, instance, mocker):
    mocker.patch('requests.Session.get', side_effect=ConnectionError('connection refused'))
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'dell_powerflex.api.can_connect',
        value=0,
        tags=['powerflex_gateway_url:https://localhost:443'],
    )


def test_can_connect_up(dd_run_check, aggregator, instance, mocker):
    mocker.patch('requests.Session.get', return_value=MagicMock(raise_for_status=MagicMock()))
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'dell_powerflex.api.can_connect',
        value=1,
        tags=['powerflex_gateway_url:https://localhost:443'],
    )


def test_collect_system(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    base_tags = ['powerflex_gateway_url:https://localhost:443']
    system_tags = base_tags + ['system_id:1fcf40fc60c6520f']

    aggregator.assert_metric('dell_powerflex.api.can_connect', value=1, tags=base_tags)

    for metric in SYSTEM_MDM_CLUSTER_METRICS:
        aggregator.assert_metric(
            metric['name'],
            value=metric['value'],
            tags=system_tags + metric.get('extra_tags', []),
        )

    for metric in SYSTEM_STATS_SIMPLE_METRICS:
        aggregator.assert_metric(metric['name'], value=metric['value'], tags=system_tags)

    for metric_prefix in SYSTEM_STATS_BWC_METRICS:
        aggregator.assert_metric(f'{metric_prefix}.num_seconds', value=0, tags=system_tags)
        aggregator.assert_metric(f'{metric_prefix}.total_weight_in_kb', value=0, tags=system_tags)
        aggregator.assert_metric(f'{metric_prefix}.num_occured', value=0, tags=system_tags)

    aggregator.assert_all_metrics_covered()


def test_assert_all_metrics(dd_run_check, aggregator, instance, mock_http_get):
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)
    for metric_name in get_metadata_metrics():
        aggregator.assert_metric(metric_name, at_least=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_collect_system_with_name(dd_run_check, aggregator, instance, mocker):
    instances_response = [
        {
            'id': '1fcf40fc60c6520f',
            'name': 'my-powerflex',
            'mdmCluster': {
                'goodNodesNum': 3,
                'goodReplicasNum': 2,
                'clusterState': 'ClusteredNormal',
                'clusterMode': 'ThreeNodes',
            },
        }
    ]

    def mock_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=instances_response if 'types/System/instances' in url else {})
        return resp

    mocker.patch('requests.Session.get', side_effect=mock_get)
    check = DellPowerflexCheck('dell_powerflex', {}, [instance])
    dd_run_check(check)

    system_tags = ['powerflex_gateway_url:https://localhost:443', 'system_id:1fcf40fc60c6520f', 'system_name:my-powerflex']
    aggregator.assert_metric('dell_powerflex.system.mdm_cluster.good_nodes', value=3, tags=system_tags)
    aggregator.assert_metric('dell_powerflex.system.mdm_cluster.good_replicas', value=2, tags=system_tags)
