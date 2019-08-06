# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    expected_tags = ["instance:{}-{}".format(instance.get("host"), instance.get("port", 22))]

    aggregator.assert_metric("sftp.response_time", tags=expected_tags)

    common.wait_for_threads()
