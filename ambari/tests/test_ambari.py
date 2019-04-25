# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ambari import AmbariCheck


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




