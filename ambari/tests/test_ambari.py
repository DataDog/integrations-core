# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ambari import AmbariCheck


def test_check(aggregator):
    instance = [{
        "url": "c6801.ambari.apache.org",
        "port": "8080",
        "username": "admin",
        "password": "admin"
    }]
    check = AmbariCheck('ambari', {}, {}, instance)

    check.check(instance[0])
    aggregator.assert_all_metrics_covered()
