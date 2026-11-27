# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import assert_check_kafka
from .conftest import reported_batched_groups

pytestmark = [pytest.mark.e2e]


def test_e2e(dd_agent_check, kafka_instance):
    aggregator = dd_agent_check(kafka_instance)
    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])


def test_e2e_reports_every_consumer_group_when_requests_are_batched(dd_agent_check, batched_consumer_groups):
    instance, group_ids = batched_consumer_groups

    aggregator = dd_agent_check(instance)

    assert reported_batched_groups(aggregator) == {f'consumer_group:{group}' for group in group_ids}
