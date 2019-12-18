# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest


@pytest.mark.usefixtures('dd_environment')
def test_metadata(check, instance, datadog_agent):
    check.check_id = 'test:123'

    version = os.environ['RABBITMQ_VERSION']
    major, minor = version.split('.')

    version_metadata = {'version.scheme': 'semver', 'version.major': major, 'version.minor': minor}

    check.check(instance)

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata) + 2)
