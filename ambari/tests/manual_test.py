# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.ambari import AmbariCheck


@pytest.mark.skip(reason="Cannot be automated due to network restrictions")
def test_ambari(aggregator):
    ambari_ip = "localhost"
    init_config = {"collect_host_metrics": True, "collect_service_metrics": True, "collect_service_status": True}
    instances = [
        {
            "url": "https://{}:8443/ambari-lab-2/dp-proxy/ambari".format(ambari_ip),
            "username": "admin",
            "password": "admin",
            "tags": ["test:manual"],
            "services": {
                "HDFS": {"NAMENODE": [], "DATANODE": []},
                "YARN": {"NODEMANANGER": ["cpu", "disk", "load", "memory", "network", "process"], "YARNCLIENT": []},
                "MAPREDUCE2": {"HISTORYSERVER": ["BufferPool", "Memory", "jvm"]},
            },
            "timeout": 30,
            "tls_verify": False,
        }
    ]
    check = AmbariCheck(init_config=init_config, instances=instances)
    check.check(instances[0])
    aggregator.assert_all_metrics_covered()
