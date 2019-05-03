# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.ambari import AmbariCheck


@pytest.mark.skip(reason="Cannot be automated due to network restrictions")
def test_check(aggregator):
    instance = [{
        "url": "https://localhost:6789/ambari-lab-2/dp-proxy/ambari",
        "username": "admin",
        "password": "admin",
        "tags": ["test:manual"],
        "services": {
            "HDFS": ["NAMENODE", "DATANODE"],
            "YARN": ["NODEMANANGER", "YARNCLIENT"],
            "SPARK": []
        },
        "metric_headers": ["cpu", "jvm"],
        "collect_host_metrics": True,
        "collect_service_metrics": True,
        "collect_service_status": True,
        "timeout": 30,
        "tls_verify": False,
    }]
    check = AmbariCheck(instances=instance)
    check.check(instance[0])
    # import pdb; pdb.set_trace()
    aggregator.assert_all_metrics_covered()
