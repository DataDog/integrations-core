# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from .common import _test_check

log = logging.getLogger('test_elastic')

pytestmark = pytest.mark.e2e


def test_e2e(dd_agent_check, elastic_check, instance, cluster_tags, node_tags):
    aggregator = dd_agent_check(instance, rate=True)
    _test_check(elastic_check, instance, aggregator, cluster_tags, node_tags)
