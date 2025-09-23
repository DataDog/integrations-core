# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.cockroachdb import CockroachdbCheck

from ..common import COCKROACHDB_VERSION
from .common import assert_check

pytestmark = [pytest.mark.usefixtures("dd_environment")]


def test_integration(aggregator, instance_legacy, dd_run_check):
    check = CockroachdbCheck('cockroachdb', {}, [instance_legacy])
    dd_run_check(check)

    assert_check(aggregator)


def test_version_metadata(aggregator, instance_legacy, datadog_agent, dd_run_check):
    check_instance = CockroachdbCheck('cockroachdb', {}, [instance_legacy])
    check_instance.check_id = 'test:123'
    dd_run_check(check_instance)

    if COCKROACHDB_VERSION == 'latest':
        m = aggregator._metrics['cockroachdb.build.timestamp'][0]
        # extract version from tags that looks like this: ['tag:v19.2.4', 'go_version:go1.12.12']
        version_label = [t for t in m.tags if 'tag' in t]
        assert len(version_label) == 1
        raw_version = version_label[0].split(':', 1)[1]
    else:
        raw_version = COCKROACHDB_VERSION

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major.lstrip('v'),
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
