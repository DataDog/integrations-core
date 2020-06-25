# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev import run_command
from datadog_checks.ibm_mq import IbmMqCheck

pytestmark = pytest.mark.e2e


def test_metadata(instance_metadata, datadog_agent):
    check = IbmMqCheck('ibm_mq', {}, [instance_metadata])
    check.check_id = 'test:123'
    check.check(instance_metadata)

    cmd = ["docker", "exec", "ibm_mq", "dspmqver"]
    result = run_command(cmd, capture="out", check=True)

    raw_version = IbmMqCheck._parse_version(result.stdout)
    major, minor, patch, _ = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
