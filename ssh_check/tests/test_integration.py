# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    check.check(instance)
    common._test_check(aggregator, instance)
    common.wait_for_threads()


def test_metadata(aggregator, check, instance, datadog_agent):
    check.check_id = 'test:123'

    nb_threads = threading.active_count()

    check.check(instance)

    raw_version = '8.1.1'

    major, minor, patch = raw_version.split(".")

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)

    # Check that we've closed all connections, if not we're leaking threads
    common.wait_for_threads()
    assert nb_threads == threading.active_count()
