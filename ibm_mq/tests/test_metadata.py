# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import MQ_VERSION_RAW, skip_windows_ci


@skip_windows_ci
@pytest.mark.integration
def test_metadata(get_check, instance, datadog_agent):
    check = get_check(instance)
    check.check_id = 'test:123'
    check.check(instance)

    raw_version = MQ_VERSION_RAW
    major, minor, mod, fix = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'ibm_mq',
        'version.major': major,
        'version.minor': minor,
        'version.mod': mod,
        'version.fix': fix,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
