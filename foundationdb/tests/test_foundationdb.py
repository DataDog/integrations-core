# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Any, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.foundationdb import FoundationdbCheck

from .common import METRICS, PROTOCOL

current_dir = dir_path = os.path.dirname(os.path.realpath(__file__)) + '/'


def test_partial(aggregator, instance):
    with open(current_dir + 'partial.json', 'r') as f:
        data = json.loads(f.read())
        check = FoundationdbCheck('foundationdb', {}, [instance])
        check.check_metrics(data)
        aggregator.assert_service_check("foundationdb.can_connect", AgentCheck.OK)


def test_full(aggregator, instance):
    with open(current_dir + 'full.json', 'r') as f:
        instance['tags'] = ['fdb_test:true']
        data = json.loads(f.read())
        check = FoundationdbCheck('foundationdb', {}, [instance])
        check.check_metrics(data)

        for metric in METRICS:
            aggregator.assert_metric(metric)
            aggregator.assert_metric_has_tag(metric, 'fdb_test:true')

            if metric.startswith('foundationdb.process.'):
                aggregator.assert_metric_has_tag_prefix(metric, 'fdb_process_class')
                aggregator.assert_metric_has_tag_prefix(metric, 'fdb_role')

        aggregator.assert_metric(
            'foundationdb.process.cpu.usage_cores',
            tags=[
                'fdb_test:true',
                'fdb_process:127.0.0.1:4000',
                'fdb_process_class:unset',
                'fdb_role:master',
                'fdb_role:cluster_controller',
                'fdb_role:data_distributor',
                'fdb_role:ratekeeper',
                'fdb_role:coordinator',
                'fdb_role:proxy',
                'fdb_role:log',
                'fdb_role:storage',
                'fdb_role:resolver',
            ],
            value=0.015280199999999999,
        )

        aggregator.assert_all_metrics_covered()
        aggregator.assert_metrics_using_metadata(get_metadata_metrics())
        aggregator.assert_service_check("foundationdb.can_connect", AgentCheck.OK)

        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_process_class:unset")

        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:master")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:cluster_controller")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:data_distributor")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:ratekeeper")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:coordinator")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:proxy")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:log")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:storage")
        aggregator.assert_metric_has_tag("foundationdb.processes_per_role", "fdb_role:resolver")


@pytest.mark.skipif(PROTOCOL == 'tls', reason="Non-TLS FoundationDB cluster only.")
@pytest.mark.usefixtures("dd_environment")
def test_integ(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = FoundationdbCheck('foundationdb', {}, [instance])
    check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("foundationdb.can_connect", AgentCheck.OK)


@pytest.mark.skipif(PROTOCOL == 'tls', reason="Non-TLS FoundationDB cluster only.")
@pytest.mark.usefixtures("dd_environment")
def test_custom_metrics(aggregator, instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    instance['custom_queries'] = [
        {
            'metric_prefix': 'custom',
            'query_key': 'basket_size',
            'query_type': 'count',
            'tags': ['query:custom'],
        },
        {
            'metric_prefix': 'another_custom_one',
            'query_key': 'temperature',
            'query_type': 'gauge',
            'tags': ['query:another_custom_one'],
        },
    ]
    check = FoundationdbCheck('foundationdb', {}, [instance])
    check.check(instance)
    aggregator.assert_metric('custom.basket_size')
    aggregator.assert_metric('another_custom_one.temperature')
    del instance['custom_queries']


@pytest.mark.skipif(PROTOCOL != 'tls', reason="TLS FoundationDB cluster only.")
@pytest.mark.usefixtures("dd_environment")
def test_tls_integ(aggregator, tls_instance):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = FoundationdbCheck('foundationdb', {}, [tls_instance])
    check.check(tls_instance)

    for metric in METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("foundationdb.can_connect", AgentCheck.OK)
