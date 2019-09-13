# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import iteritems

from .common import get_e2e_instance, get_queue_counts


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check(get_e2e_instance())

    for queue, count in iteritems(get_queue_counts()):
        tags = ['instance:postfix_data', 'queue:{}'.format(queue)]
        aggregator.assert_metric('postfix.queue.size', value=count[0], tags=tags)
