# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.fluentd import Fluentd

from .common import CHECK_NAME, FLUENTD_CONTAINER_NAME, FLUENTD_VERSION, HERE

CHECK_ID = 'test:123'
VERSION_MOCK_SCRIPT = os.path.join(HERE, 'mock', 'fluentd_version.py')


@pytest.mark.usefixtures("dd_environment")
def test_collect_metadata_instance(aggregator, datadog_agent, instance):
    instance['fluentd'] = 'docker exec {} fluentd'.format(FLUENTD_CONTAINER_NAME)

    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    major, minor, patch = FLUENTD_VERSION.split('.')
    version_metadata = {
        'version.raw': FLUENTD_VERSION,
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    datadog_agent.assert_metadata(CHECK_ID, version_metadata)
    datadog_agent.assert_metadata_count(5)


@pytest.mark.usefixtures("dd_environment")
def test_collect_metadata_missing_version(aggregator, datadog_agent, instance):
    instance["fluentd"] = "python {} 'fluentd not.a.version'".format(VERSION_MOCK_SCRIPT)

    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    datadog_agent.assert_metadata(CHECK_ID, {})
    datadog_agent.assert_metadata_count(0)


@pytest.mark.usefixtures("dd_environment")
def test_collect_metadata_invalid_binary(datadog_agent, instance):
    instance['fluentd'] = '/bin/does_not_exist'

    check = Fluentd(CHECK_NAME, {}, [instance])
    check.check_id = CHECK_ID
    check.check(instance)

    datadog_agent.assert_metadata(CHECK_ID, {})
    datadog_agent.assert_metadata_count(0)
