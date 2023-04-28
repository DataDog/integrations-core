# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.azure_iot_edge.config import Config
from datadog_checks.azure_iot_edge.metrics import EDGE_AGENT_METRICS, EDGE_AGENT_TYPE_OVERRIDES, EDGE_HUB_METRICS
from datadog_checks.azure_iot_edge.types import Instance  # noqa: F401
from datadog_checks.base import ConfigurationError


@pytest.mark.unit
def test_config():
    # type: () -> None
    instance = {
        'edge_hub_prometheus_url': 'http://testserver:9601/metrics',
        'edge_agent_prometheus_url': 'http://testserver:9602/metrics',
    }  # type: Instance

    config = Config(instance)

    assert config.prometheus_instances == [
        {
            'prometheus_url': 'http://testserver:9601/metrics',
            'namespace': 'edge_hub',
            'metrics': EDGE_HUB_METRICS,
            'tags': [],
            'exclude_labels': ['ms_telemetry', 'instance_number'],
        },
        {
            'prometheus_url': 'http://testserver:9602/metrics',
            'namespace': 'edge_agent',
            'metrics': EDGE_AGENT_METRICS,
            'type_overrides': EDGE_AGENT_TYPE_OVERRIDES,
            'tags': [],
            'exclude_labels': ['ms_telemetry', 'instance_number'],
            'metadata_metric_name': 'edgeAgent_metadata',
            'metadata_label_map': {'version': 'edge_agent_version'},
        },
    ]


@pytest.mark.unit
def test_config_custom_tags():
    # type: () -> None
    tags = ['env:testing']
    instance = {
        'edge_hub_prometheus_url': '...',
        'edge_agent_prometheus_url': '...',
        'tags': tags,
    }  # type: Instance

    config = Config(instance)

    for instance in config.prometheus_instances:
        assert instance['tags'] == tags


@pytest.mark.unit
@pytest.mark.parametrize('key', ['edge_hub_prometheus_url', 'edge_agent_prometheus_url'])
def test_config_required_options(key):
    # type: (str) -> None
    instance = {
        'edge_hub_prometheus_url': '...',
        'edge_agent_prometheus_url': '...',
    }  # type: Instance

    instance.pop(key)  # type: ignore

    with pytest.raises(ConfigurationError):
        _ = Config(instance)


@pytest.mark.unit
def test_config_tags_must_be_list():
    # type: () -> None
    instance = {
        'edge_hub_prometheus_url': '...',
        'edge_agent_prometheus_url': '...',
        'tags': 'string:tags',  # type: ignore
    }  # type: Instance

    with pytest.raises(ConfigurationError):
        _ = Config(instance)
