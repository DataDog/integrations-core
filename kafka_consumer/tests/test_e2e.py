# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import assert_check_kafka

pytestmark = [pytest.mark.e2e]


def test_e2e(dd_agent_check, kafka_instance):
    aggregator = dd_agent_check(kafka_instance)
    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])
