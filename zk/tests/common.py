# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.zk import ZookeeperCheck


def assert_service_checks_ok(aggregator):
    aggregator.assert_service_check("zookeeper.ruok", status=ZookeeperCheck.OK)
    aggregator.assert_service_check("zookeeper.mode", status=ZookeeperCheck.OK)
