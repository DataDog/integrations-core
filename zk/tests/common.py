# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

from packaging.version import Version

from datadog_checks.zk import ZookeeperCheck

from .metrics import LATENCY_METRICS, METRICS_34, METRICS_36, METRICS_36_OPTIONAL, STAT_METRICS

ZK_VERSION = os.environ['ZK_VERSION']

ZK_CLICKHOUSE_PAYLOAD = """ZClickHouse Keeper version: v22.9.1.15416-testing-6156f9cd99b5efd5fe1eeab391571deb4176e2af
Clients:
/172.29.0.1:60620[1](queued=0,recved=1,sent=0)

Latency min/avg/max: 0/0.0/0
Received: 2
Sent: 1
Connections: 1
Outstanding: 0
Zxid: 0x0
Mode: standalone
Node count: 5
"""


def assert_service_checks_ok(aggregator):
    aggregator.assert_service_check("zookeeper.ruok", status=ZookeeperCheck.OK)
    aggregator.assert_service_check("zookeeper.mode", status=ZookeeperCheck.OK)


def assert_stat_metrics(aggregator):
    for mname in STAT_METRICS:
        aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])


def assert_latency_metrics(aggregator):
    for mname in LATENCY_METRICS:
        aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"], at_least=0)


def assert_mntr_metrics_by_version(aggregator, skip=None):
    if skip is None:
        skip = []
    skip = set(skip)

    zk_version = os.environ.get("ZK_VERSION") or "3.4.10"
    metrics_to_check = METRICS_34
    optional_metrics = []
    if zk_version and Version(zk_version) >= Version("3.6"):
        metrics_to_check = METRICS_36
        optional_metrics = METRICS_36_OPTIONAL

    for metric in metrics_to_check:
        if metric in skip:
            continue
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag_prefix(metric, tag_prefix='mode')
        aggregator.assert_metric_has_tag_prefix(metric, tag_prefix='mytag')

    for metric in optional_metrics:
        aggregator.assert_metric(metric, at_least=0)
