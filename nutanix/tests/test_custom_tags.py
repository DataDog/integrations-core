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


def test_custom_tags_propagate_to_metrics(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    """Custom tags from ``instance['tags']`` propagate to all emitted metrics and external tags."""
    mock_instance['tags'] = CUSTOM_TAGS

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=BASE_TAGS + CUSTOM_TAGS)
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=CLUSTER_TAGS + CUSTOM_TAGS)
    aggregator.assert_metric("nutanix.host.count", value=1, tags=HOST_TAGS + CUSTOM_TAGS, hostname=HOST_NAME)
    aggregator.assert_metric("nutanix.vm.count", value=1, tags=PCVM_TAGS + CUSTOM_TAGS)
    datadog_agent.assert_external_tags(HOST_NAME, {'nutanix': HOST_TAGS + CUSTOM_TAGS})
    datadog_agent.assert_external_tags(PCVM_NAME, {'nutanix': PCVM_TAGS + CUSTOM_TAGS})
