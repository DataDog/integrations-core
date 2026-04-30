# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import (
    BASE_TAGS,
    CLUSTER_TAGS,
    HOST_NAME,
    HOST_TAGS,
    PCVM_NAME,
    PCVM_TAGS,
)

pytestmark = [pytest.mark.unit]

CUSTOM_TAGS = ['custom_env:test', 'custom_team:agent-integrations', 'custom_key:custom_value']


def test_base_tags_include_custom_tags(dd_run_check, mock_instance, mock_http_get):
    """Custom tags from the ``tags`` config option are added to base_tags."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    for tag in CUSTOM_TAGS:
        assert tag in check.base_tags
    assert 'nutanix' in check.base_tags
    assert 'prism_central:10.0.0.197' in check.base_tags


def test_base_tags_without_custom_tags(dd_run_check, mock_instance, mock_http_get):
    """When no custom tags are configured, base_tags only contains the defaults."""
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    assert sorted(check.base_tags) == sorted(BASE_TAGS)


def test_health_metric_has_custom_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Custom tags propagate to the ``nutanix.health.up`` service metric."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=BASE_TAGS + CUSTOM_TAGS)


def test_health_metric_failure_has_custom_tags(dd_run_check, aggregator, mock_instance, mocker):
    """Custom tags are emitted with ``nutanix.health.up`` even when the connection fails."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    def mock_exception(*args, **kwargs):
        from requests.exceptions import ConnectionError

        raise ConnectionError("Connection failed")

    mocker.patch('requests.Session.get', side_effect=mock_exception)
    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1, tags=BASE_TAGS + CUSTOM_TAGS)


def test_cluster_metric_has_custom_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Custom tags propagate to cluster-level metrics."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=CLUSTER_TAGS + CUSTOM_TAGS)


def test_host_metric_has_custom_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Custom tags propagate to host-level metrics."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.count", value=1, tags=HOST_TAGS + CUSTOM_TAGS, hostname=HOST_NAME)


def test_vm_metric_has_custom_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Custom tags propagate to VM-level metrics."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=PCVM_TAGS + CUSTOM_TAGS)


def test_external_tags_include_custom_tags(dd_run_check, mock_instance, mock_http_get, datadog_agent):
    """Custom tags propagate to external tags submitted for hosts and VMs."""
    instance = mock_instance.copy()
    instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    datadog_agent.assert_external_tags(HOST_NAME, {'nutanix': HOST_TAGS + CUSTOM_TAGS})
    datadog_agent.assert_external_tags(PCVM_NAME, {'nutanix': PCVM_TAGS + CUSTOM_TAGS})


def test_empty_custom_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    """An empty ``tags`` list behaves like no custom tags configured."""
    instance = mock_instance.copy()
    instance['tags'] = []

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    assert sorted(check.base_tags) == sorted(BASE_TAGS)
    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=BASE_TAGS)


@pytest.mark.parametrize(
    "custom_tags",
    [
        pytest.param(['single_tag:value'], id="single_kv_tag"),
        pytest.param(['standalone_tag'], id="bare_tag"),
        pytest.param(['key:value', 'bare_tag', 'custom_env:prod'], id="mixed_tags"),
    ],
)
def test_custom_tags_formats(dd_run_check, aggregator, mock_instance, mock_http_get, custom_tags):
    """Custom tags support both ``key:value`` and bare formats, and any combination."""
    instance = mock_instance.copy()
    instance['tags'] = custom_tags

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=BASE_TAGS + custom_tags)
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=CLUSTER_TAGS + custom_tags)


def test_custom_tags_do_not_mutate_config(dd_run_check, mock_instance, mock_http_get):
    """Mutating ``base_tags`` must not leak back into the configured ``tags`` list."""
    instance = mock_instance.copy()
    instance['tags'] = list(CUSTOM_TAGS)

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)
    check.base_tags.append('mutated:true')

    assert 'mutated:true' not in (check.config.tags or ())
