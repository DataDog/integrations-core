# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ambari import AmbariCheck
from unittest.mock import MagicMock


def test_flatten_service_metrics():
    metrics = AmbariCheck.flatten_service_metrics({"metric_a": 10,
                                                        "metric_b": 15,
                                                        "metric_c": {"submetric_c": "hello"},
                                                        "metric_d": {"submetric_d": {'subsub_d': 25}}
                                                        }, "pfx")
    assert metrics == {'pfx.metric_a': 10,
                       'pfx.metric_b': 15,
                       'pfx.submetric_c': 'hello',
                       'pfx.subsub_d': 25
                       }


def test_flatten_host_metrics():
    metrics = AmbariCheck.flatten_host_metrics({"metric_a": 10,
                                                "metric_b": 15,
                                                "boottime": 87,
                                                "metric_c": {"submetric_c": "hello"},
                                                "metric_d": {"submetric_d": {'subsub_d': 25}}
                                                })
    assert metrics == {'metric_a': 10,
                       'metric_b': 15,
                       "boottime": 87,
                       'metric_c.submetric_c': 'hello',
                       'metric_d.submetric_d.subsub_d': 25
                       }


def test_get_clusters(instance, authentication):
    ambari = AmbariCheck(instance=instance)
    ambari.make_request = MagicMock(return_value={
        'href': 'localhost/api/v1/clusters',
        'items': [{'href': 'localhost/api/v1/clusters/LabCluster',
                   'Clusters': {'cluster_name': 'LabCluster'}}
                  ]
    })
    clusters = ambari.get_clusters('localhost', authentication)
    ambari.make_request.assert_called_with('localhost/api/v1/clusters', authentication)
    assert clusters == ['LabCluster']






