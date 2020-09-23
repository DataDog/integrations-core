# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.azure_iot_edge.check import AzureIoTEdgeCheck
from datadog_checks.azure_iot_edge.config import Config
from datadog_checks.azure_iot_edge.metrics import EDGE_AGENT_METRICS, EDGE_HUB_METRICS
from datadog_checks.azure_iot_edge.types import Instance
from datadog_checks.base import ConfigurationError


@pytest.mark.unit
def test_config():
    # type: () -> None
    instance = {
        'edge_hub_prometheus_url': 'http://testserver:9601/metrics',
        'edge_agent_prometheus_url': 'http://testserver:9602/metrics',
        'security_daemon_management_api_url': 'http://testserver:15580',
    }  # type: Instance

    config = Config(instance, check_namespace=AzureIoTEdgeCheck.__NAMESPACE__)

    assert config.edge_hub_instance == {
        'prometheus_url': 'http://testserver:9601/metrics',
        'namespace': 'azure.iot_edge.edge_hub',
        'metrics': EDGE_HUB_METRICS,
        'tags': [],
        'exclude_labels': ['ms_telemetry', 'instance_number'],
    }
    assert config.edge_agent_instance == {
        'prometheus_url': 'http://testserver:9602/metrics',
        'namespace': 'azure.iot_edge.edge_agent',
        'metrics': EDGE_AGENT_METRICS,
        'tags': [],
        'exclude_labels': ['ms_telemetry', 'instance_number'],
    }
    assert config.security_daemon_management_api_url == 'http://testserver:15580'


@pytest.mark.unit
def test_config_custom_tags():
    # type: () -> None
    tags = ['env:testing']
    instance = {
        'edge_hub_prometheus_url': '...',
        'edge_agent_prometheus_url': '...',
        'security_daemon_management_api_url': '...',
        'tags': tags,
    }  # type: Instance

    config = Config(instance, check_namespace=AzureIoTEdgeCheck.__NAMESPACE__)

    assert config.tags == tags
    assert config.edge_hub_instance['tags'] == tags
    assert config.edge_agent_instance['tags'] == tags


@pytest.mark.unit
@pytest.mark.parametrize(
    'key', ['edge_hub_prometheus_url', 'edge_agent_prometheus_url', 'security_daemon_management_api_url']
)
def test_config_required_options(key):
    # type: (str) -> None
    instance = {
        'edge_hub_prometheus_url': '...',
        'edge_agent_prometheus_url': '...',
        'security_daemon_management_api_url': '...',
    }  # type: Instance

    instance.pop(key)  # type: ignore

    with pytest.raises(ConfigurationError):
        _ = Config(instance, check_namespace=AzureIoTEdgeCheck.__NAMESPACE__)


@pytest.mark.unit
def test_config_tags_must_be_list():
    # type: () -> None
    instance = {
        'edge_hub_prometheus_url': '...',
        'edge_agent_prometheus_url': '...',
        'security_daemon_management_api_url': '...',
        'tags': 'string:tags',  # type: ignore
    }  # type: Instance

    with pytest.raises(ConfigurationError):
        _ = Config(instance, check_namespace=AzureIoTEdgeCheck.__NAMESPACE__)
