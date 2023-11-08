# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.glusterfs import GlusterfsCheck

from .common import CHECK, E2E_INIT_CONFIG, GLUSTER_VERSION

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_version_metadata(aggregator, datadog_agent, instance):
    c = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    c.check_id = 'test:123'
    c.check(instance)
    major, minor, patch = c.parse_version(GLUSTER_VERSION)

    version_metadata = {
        'version.raw': GLUSTER_VERSION,
        'version.scheme': 'glusterfs',
        'version.major': major,
        'version.minor': minor,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(4)
