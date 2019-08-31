# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import _check


@pytest.mark.e2e
def test_check(dd_agent_check, check, instance):
    tags = ["url:{}".format(instance["url"]), "test:integration"]
    aggregator = dd_agent_check(instance, rate=True)
    _check(aggregator, check, tags)
