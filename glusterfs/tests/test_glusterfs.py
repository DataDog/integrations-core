# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.glusterfs import GlusterfsCheck

from .common import CHECK, CONFIG, EXPECTED_METRICS, GLUSTER_VERSION

INIT_CONFIG = {'gstatus_path': '/usr/local/bin/gstatus'}


@pytest.mark.unit
def test_check(aggregator, instance, mock_gstatus_data):
    # type: (AggregatorStub, Dict[str, Any]) -> None
    check = GlusterfsCheck(CHECK, INIT_CONFIG, [instance])
    check.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_version_metadata(aggregator, datadog_agent):
    c = GlusterfsCheck(CHECK, CONFIG['init_config'], [{}])
    c.check_id = 'test:123'
    c.check({})

    version_metadata = {
        'version.raw': GLUSTER_VERSION,
        'version.scheme': 'glusterfs',
    }
    version_metadata.update(c.parse_version(GLUSTER_VERSION))

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(4)
