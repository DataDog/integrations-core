# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.velero import VeleroCheck


def test_generated_discovery_uses_named_metrics_ports():
    service = Service(
        id='velero',
        host='10.0.0.1',
        ports=(
            Port(number=8085, name='metrics'),
            Port(number=9999, name='admin'),
            Port(number=8086, name='http-monitoring'),
        ),
    )

    configs = list(VeleroCheck.generate_configs(service))

    assert [config['instances'][0]['openmetrics_endpoint'] for config in configs] == [
        'http://10.0.0.1:8086/metrics',
        'http://10.0.0.1:8085/metrics',
    ]
