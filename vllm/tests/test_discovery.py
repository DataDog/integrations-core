# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.vllm import vLLMCheck
from datadog_checks.vllm.config_models import discovery_overrides

pytestmark = [pytest.mark.unit]


def test_openmetrics_endpoint_candidates_prioritize_vllm_and_dynamo_ports() -> None:
    service = Service(
        id='vllm',
        host='127.0.0.1',
        ports=(Port(number=8081), Port(number=7000), Port(number=9090), Port(number=8000)),
    )

    with mock.patch.object(discovery_overrides.datadog_agent, 'get_config', return_value=True):
        instances = [config['instances'][0] for config in vLLMCheck.generate_configs(service)]

    assert [instance['openmetrics_endpoint'] for instance in instances] == [
        'http://127.0.0.1:8000/metrics',
        'http://127.0.0.1:9090/metrics',
        'http://127.0.0.1:8081/metrics',
        'http://127.0.0.1:7000/metrics',
    ]


def test_discovery_is_disabled_without_gpu_monitoring() -> None:
    service = Service(id='vllm', host='127.0.0.1', ports=(Port(number=8000),))

    with mock.patch.object(discovery_overrides.datadog_agent, 'get_config', return_value=False):
        assert list(vLLMCheck.generate_configs(service)) == []
