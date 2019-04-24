# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.ambari.common import create_endpoint


def test_create_endpoint():
    endpoint = create_endpoint("myserver", "5678", "mycluster", "hive", "/metrics")
    assert endpoint == "http://myserver:5678/api/v1/clusters/mycluster/services/HIVE/metrics"

