# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixture("dd_environment")
def test_check(aggregator, check):
    check.check(deepcopy(common.INSTANCE))

    expected_tags = ['foo:bar', 'target_host:datadoghq.com', 'port:80', 'instance:UpService']
    aggregator.assert_metric('network.tcp.can_connect', value=1, tags=expected_tags)
    aggregator.assert_service_check('tcp.can_connect', status=check.OK, tags=expected_tags)
