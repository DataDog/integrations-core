# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck


def assert_service_checks_ok(aggregator):
    aggregator.assert_service_check('hazelcast.can_connect', ServiceCheck.OK)
    aggregator.assert_service_check('hazelcast.mc_cluster_state', ServiceCheck.OK)
